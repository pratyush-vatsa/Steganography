# Deployment Notes: Google Cloud e2-micro (Always Free)

This is a real, working runbook from an actual deployment - not a generic
guide. It captures the specific gotchas hit along the way so they don't need
to be re-diagnosed next time. Live result: **https://securesteganography.com**

Environment this was done on: GCP e2-micro, `us-central1`, Ubuntu 26.04 LTS
("resolute").

---

## 1. Create the VM

Compute Engine -> VM Instances -> Create Instance:
- Region: `us-central1` (also valid: `us-west1`, `us-east1`) - only these
  three qualify for the Always Free e2-micro
- Machine type: `e2-micro`
- Boot disk: Ubuntu, Standard persistent disk (not SSD/Balanced - not free)
- Firewall: check **"Allow HTTP traffic"** and **"Allow HTTPS traffic"**

Confirm the checkboxes actually took effect - Compute Engine -> click the
instance -> **Network tags** should show `http-server`, `https-server`. If
empty, add them via Edit -> Network tags -> Save (no reboot needed).

## 2. The Python 3.14 problem (specific to newer Ubuntu images)

**Symptom:** `pip install -r requirements.txt` fails while building `numpy`
from source, ending in:
```
c++: fatal error: Killed signal terminated program cc1plus
```

**Cause:** Ubuntu 26.04 ships **Python 3.14** as the system default.
`numpy==1.26.4` (pinned in `requirements.txt`) predates Python 3.14 and has
no prebuilt wheel for it, so pip falls back to compiling from source -
which is memory-hungry (numpy's SIMD dispatch code is heavily templated) and
gets OOM-killed on e2-micro's 1GB RAM. Not a bug in this project - just an
old pin meeting a very new default interpreter.

**What didn't work:** installing Python 3.12 via the deadsnakes PPA.
Deadsnakes' own docs list `python3.12 (jammy, resolute)` as available, but
in practice `apt install python3.12` still returned "Package python3.12 is
not available." Don't spend time on this path - go straight to the fix
below.

**What worked:** keep the system's Python 3.14, and let newer versions of
just the four scientific packages resolve automatically (they have 3.14
wheels; the exact pinned versions in `requirements.txt` don't):
```bash
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install Flask==3.0.3 python-dotenv==1.0.1 gunicorn==22.0.0 \
    Pillow==12.3.0 pillow-heif==1.5.0 pycryptodome==3.20.0
venv/bin/pip install numpy pandas matplotlib scikit-image
```
The first command installs everything that's already fine at its pinned
version. The second, with no version pins, lets pip pick current releases
of numpy/pandas/matplotlib/scikit-image that ship 3.14 wheels (this pulled
in numpy 2.5.1, pandas 3.0.5, matplotlib 3.11.1, scikit-image 0.26.0 -
newer than what's pinned in `requirements.txt`, and all confirmed working).

Verify before moving on:
```bash
venv/bin/python -c "from PIL import Image; import numpy, pandas, matplotlib, skimage; print('All imports OK')"
```

**If you hit this on a fresh Ubuntu 22.04/24.04 VM instead:** those ship
Python 3.10/3.12 respectively, both of which are fully covered by the
pinned versions in `requirements.txt` - `pip install -r requirements.txt`
should just work with no source builds at all.

## 3. Add a swapfile (cheap insurance on a 1GB VM)

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 4. `.env`

```bash
printf "SECRET_KEY=%s\n" "$(venv/bin/python -c 'import secrets;print(secrets.token_hex(32))')" > .env
echo "STEGO_BASE_DIR=/tmp/stego-data" >> .env
echo "MAX_IMAGE_MEGAPIXELS=8" >> .env
```
`MAX_IMAGE_MEGAPIXELS=8` (not the project default of 30) matters specifically
because e2-micro only has 1GB RAM.

## 5. systemd service - four lines need editing, not three

`deploy/stego.service` has **four** placeholder paths, easy to miss one:
```
User=ubuntu
WorkingDirectory=/home/ubuntu/stego-app
EnvironmentFile=/home/ubuntu/stego-app/.env      <- easy to miss this one
ExecStart=/home/ubuntu/stego-app/venv/bin/gunicorn run:app --workers 1 --timeout 120 --bind 127.0.0.1:8000
```
All four need your real username and path, e.g.:
```
User=pratyushvatsa11
WorkingDirectory=/home/pratyushvatsa11/Steganography
EnvironmentFile=/home/pratyushvatsa11/Steganography/.env
ExecStart=/home/pratyushvatsa11/Steganography/venv/bin/gunicorn run:app --workers 1 --timeout 120 --bind 127.0.0.1:8000
```
Missing the `EnvironmentFile` line specifically produces a vague
`"Job for stego.service failed because of unavailable resources or another
system error"` with no obvious cause - if you hit that error, check this
line first.

```bash
sudo cp deploy/stego.service /etc/systemd/system/stego.service
sudo nano /etc/systemd/system/stego.service   # edit all four lines
sudo systemctl daemon-reload
sudo systemctl enable --now stego
sudo systemctl status stego                   # want: active (running)
```
(`systemctl status` opens a pager - press `q` to exit it; this does not
stop the service, it's just closing the read-only viewer.)

If `sudo` itself starts refusing commands with an odd "insults" message,
that's `sudo`'s built-in easter egg on an auth hiccup, not a real
permissions problem - close the SSH tab and reopen a fresh session via the
Console's SSH button.

### This file gets overwritten back to the generic template on every future sync

`deploy/stego.service` in the repo is a **template** - it doesn't know your
real username or path. Every time you `git pull` and then `cp` it over the
live systemd file again (e.g. to pick up an unrelated change like a
`--workers` count adjustment), it silently wipes your customization back
to `User=ubuntu` / `/home/ubuntu/stego-app`. Not a bug, just what "copying
a version-controlled template" means - but easy to be caught out by.

**Fix: always follow the `cp` with a `sed` that reapplies your values in
the same step**, rather than reaching for `nano` again:
```bash
sudo cp deploy/stego.service /etc/systemd/system/stego.service
sudo sed -i 's|/home/ubuntu/stego-app|/home/pratyushvatsa11/Steganography|g; s|User=ubuntu|User=pratyushvatsa11|' /etc/systemd/system/stego.service
```
Verify before restarting: `cat /etc/systemd/system/stego.service`.

**Even simpler for a small, known change** (like a worker-count tweak):
skip re-copying the template at all, and patch just that one line directly
on the already-customized live file:
```bash
sudo sed -i 's/--workers 2/--workers 1/' /etc/systemd/system/stego.service
```

## 6. nginx

```bash
sudo cp deploy/nginx-stego.conf /etc/nginx/sites-available/stego
sudo ln -s /etc/nginx/sites-available/stego /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 7. If the site doesn't load: diagnostic order that actually worked

Check in this order - each one ruled out a layer until the real cause
turned up:

1. `curl -I http://localhost/` on the VM - confirms nginx+gunicorn work at
   all, independent of any external networking.
2. `sudo ufw status verbose` - confirms the OS firewall allows 80/443.
3. `sudo ss -tlnp | grep :80` - confirms nginx is bound to `0.0.0.0:80`
   (all interfaces), not just `127.0.0.1:80`.
4. GCP Console -> instance details -> **Network tags** - confirms
   `http-server`/`https-server` are attached to the actual instance.
5. GCP Console -> VPC Network -> Firewall -> `default-allow-http` - confirms
   the rule targets those tags, allows `tcp:80`, source `0.0.0.0/0`.
6. `curl -I http://<external-ip>/` from a completely different machine/
   network (e.g. phone on mobile data) - if this works, the server is fine
   and the problem is local to whatever device/network failed originally.

**What the actual problem turned out to be:** every layer above checked out
fine, but one specific Windows laptop's Chrome and Firefox both refused to
load the site (`ERR_CONNECTION_REFUSED`), while `Test-NetConnection` and
`curl.exe` from the same machine succeeded. Turned off VPN, tried a phone
hotspot, tried a different browser - none of it changed anything, which
ruled out network/OS-level causes and pointed at something injected by a
specific browser extension. **Confirmed by opening the site in an Incognito
window, where it loaded fine** (Incognito disables extensions by default).
The real fix ended up being a domain + HTTPS (see below) rather than
hunting down the specific extension - a bare IP over plain HTTP is exactly
the pattern ad-blocker/security extensions tend to flag as suspicious, and
that class of block generally disappears once there's a real domain and a
valid certificate.

## 8. Static IP (promote, don't reserve new)

VPC Network -> IP addresses -> find your instance's current IP (type:
**Ephemeral**) -> three-dot menu -> **"Promote to static IP address"** ->
give it a name -> Reserve.

Do **not** use the separate "Reserve a static address" form for this - that
creates a *new*, different IP address. Promoting keeps the exact IP you're
already using (and that any DNS records already point to).

Attached to a running instance, a static IP costs nothing extra - the
warning about hourly billing only applies to a static IP sitting
**unattached**.

## 9. Domain + DNS (registrar: Spaceship, domain: securesteganography.com)

At the registrar's DNS management page, add two A records:
| Type | Host | Value | 
|---|---|---|
| A | `@` | `<your static IP>` |
| A | `www` | `<your static IP>` |

Remove any pre-existing "parked page" A record the registrar auto-added.
Propagation took only a few minutes in practice. Confirm from the VM:
```bash
nslookup securesteganography.com
```

## 10. HTTPS (certbot) - one gotcha here too

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d securesteganography.com -d www.securesteganography.com
```
This issues the certificate successfully but can fail the last step
("Deploying certificate... Could not install certificate") with:
```
Could not automatically find a matching server block for securesteganography.com.
```
**Cause:** `nginx-stego.conf` ships with `server_name _;` (a wildcard, so it
works for a bare IP) - certbot's nginx plugin needs a server block whose
`server_name` *literally* matches the domain to know where to insert the
SSL config.

**Fix:**
```bash
sudo nano /etc/nginx/sites-available/stego
# change:  server_name _;
# to:      server_name securesteganography.com www.securesteganography.com;
sudo nginx -t && sudo systemctl reload nginx
sudo certbot install --cert-name securesteganography.com
```
(`--cert-name` here refers to the *already-issued* certificate, which
covers both domains despite only naming one - it's a different flag from
the `-d` used when requesting the certificate. `sudo certbot certificates`
lists exactly which domains any given certificate covers, if unsure.)

Auto-renewal is already scheduled by the certbot package (a systemd timer)
- nothing further to set up.

---

## Redeploying after making code changes

Once this initial setup is done, shipping an update doesn't require
repeating any of the above - firewall, DNS, nginx, and the SSL certificate
all stay as they are. Only these steps repeat:

```bash
cd ~/Steganography

# get the new code - either:
git pull                                    # if using git
# or: upload the new zip via the SSH window's gear icon -> Upload file,
#     then unzip it over the existing folder

# only if requirements.txt changed:
venv/bin/pip install -r requirements.txt

# restart the app:
sudo systemctl restart stego
sudo systemctl status stego                 # confirm: active (running)
```

Pure frontend changes (HTML/CSS/JS) take effect immediately on restart with
no other steps. Setting up `git` on the VM (`git clone` your GitHub repo
instead of re-uploading zips) is worth doing if you'll be iterating - it
turns the update step into just `git pull && sudo systemctl restart stego`.

## Real incident: OOM kills during hide/batch-hide (1GB VM)

**Symptom:** the frontend showed "Network error... Unexpected token '<' is
not valid JSON" during hide and batch-hide specifically - never during
extraction. `sudo journalctl -u stego -n 100` showed the actual cause:
```
systemd[1]: stego.service: The kernel OOM killer killed some processes in this unit.
gunicorn[...]: [ERROR] Worker (pid:...) was sent SIGKILL! Perhaps out of memory?
```
and nginx's error log confirmed the client-visible symptom:
```
upstream prematurely closed connection while reading response header from upstream
```

**Root cause, measured directly** (not guessed): the PSNR/SSIM calculation
is the peak-memory moment of a hide request. Measured peak RSS across
several image sizes on this exact codebase:

| Image size | Megapixels | Peak memory |
|---|---|---|
| 1500x1000 | 1.5 MP | 180 MB |
| 2000x1500 | 3.0 MP | 292 MB |
| 2400x1600 | 3.84 MP | 363 MB |
| (extrapolated) | 8 MP | ~687 MB |

This fits a simple model: **~63MB baseline + ~78MB per megapixel**. The
`MAX_IMAGE_MEGAPIXELS=8` setting (a reasonable-sounding default) predicts
~687MB for a single request - and with e2-micro's 1GB total RAM minus
~150-250MB of OS/nginx/systemd overhead, that leaves too little margin,
especially with the default `--workers 2` allowing two such requests to
run concurrently and combine to exceed available RAM.

**Fix applied:**
- `deploy/start.sh` and `deploy/stego.service`: `--workers 2` -> `--workers 1`
  (halves baseline memory, and guarantees only one hide/extract request's
  memory footprint exists at a time)
- Recommended `.env` setting for *this specific 1GB VM* tightened from
  `MAX_IMAGE_MEGAPIXELS=8` to `MAX_IMAGE_MEGAPIXELS=4` (predicts ~375MB
  peak, leaving real headroom)

If you ever move to a VM with 2GB+ RAM, both of these can be relaxed back
up - the numbers above scale linearly, so use them to size the limit for
whatever host you're actually running on: `safe_MP ≈ (available_MB - 150) / 78`.

## Alternative to all the memory tuning above: just upgrade the instance

Everything in the incident above is about staying within e2-micro's 1GB
RAM. If handling full-resolution photos matters more than staying on the
free tier, upgrading the machine type sidesteps the tuning entirely - no
rebuild needed, since it's the same instance, just resized:

1. Compute Engine -> VM instances -> click the instance -> **Stop**
2. **Edit** -> change **Machine type** to `e2-small` (2GB RAM) or
   `e2-medium` (4GB RAM)
3. **Start**
4. Static IP, firewall rules, nginx config, and the SSL certificate are
   all untouched - only revisit `.env`'s `MAX_IMAGE_MEGAPIXELS` and the
   systemd `--workers` value to take advantage of the new headroom (use
   the same `safe_MP` formula above), then `sudo systemctl restart stego`.

This leaves GCP's Always Free tier - only `e2-micro` is free. Pricing
sources disagreed with each other by a wide margin when checked (roughly
$12-36/month for e2-small, $40-80/month for e2-medium, in us-central1) -
check Google's own current pricing calculator for an exact figure rather
than trusting either number here.

