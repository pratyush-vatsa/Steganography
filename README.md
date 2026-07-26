# Enhanced Secure Message Steganography

A web-based steganography app: hide secret messages inside images using
LSB (Least Significant Bit) embedding, with optional AES-256 encryption,
intensity-based adaptive channel selection, and batch processing with
performance metrics (PSNR, SSIM, BER, capacity).

This is a restructured version of the original `Stego-TESTING-11` project.
Functionality is unchanged except for one important bugfix (see below) and
some hardening around configuration and error handling. Everything else -
the UI, the steganography algorithm, the metrics, the batch processing -
works exactly the way it did before.

## What changed from the original project

**Structure**
- Reorganized into a standard Flask "application factory + blueprints" layout
  (see `app/` below) instead of one large `app12.py`.
- Renamed `app12.py` -> `app/routes/{pages,api}.py`, `stegfile.py` ->
  `app/core/steganography.py`, `templates/index1.html` -> `app/templates/index.html`.
- Deployment configs moved into `deploy/`.
- Removed the committed `venv/`, `__pycache__/`, and empty leftover
  directories (`Images/`, `keys/`, `output/`, `svd/`, `dvbsb/`, `.vscode/`)
  that had ended up in the project folder.
- Pinned dependency versions in `requirements.txt`.
- Added a minimal `tests/` smoke test suite (pytest).

**Bugfix (important)**
`extract_message()` speculatively reads 72 raw bits from the image up
front (enough for the largest possible header, in case a key is
embedded). When **no** key is embedded, the real header is only 40 bits -
but the original code discarded bits 40-71 as if they were unused padding.
They weren't: they're already the first 32 bits of the real message. That
silently dropped 32 bits from the front of the payload and shifted
everything after it, corrupting every message hidden with `embedKey`
turned off (and causing AES extraction to fail with a padding error, since
the corrupted bytes no longer formed a valid block). This is now fixed in
`app/core/steganography.py`. It was present in the original app - not
something introduced by the restructuring - and was verified against the
unmodified original code before being fixed here.

**Bugfix #2 (important) - adaptive channel selection could pick different
channels at extraction than at embedding**
Enhanced/adaptive mode picks which 2 of 3 RGB channels to embed into based
on each pixel's average intensity (`<85` -> R,G; `85-170` -> G,B; `>170`
-> R,B). Embedding a bit changes that same pixel's intensity by up to ~1
(from flipping a channel's LSB). Without masking that LSB out before
computing intensity, a pixel whose *original* intensity sits right at 85
or 170 can cross the threshold once embedded - so extraction (which
recomputes intensity from the now-modified pixel) picks a different
channel pair than embedding used, corrupting the payload at that pixel.
This also affected the "embed key in image" feature's master-key
derivation, which reads pixel `(0,0)` among others - the very first pixel
embedding ever touches.

This surfaces on some images and not others: flat-color illustrations
(large areas of near-identical color - skies, skin, fabric) are far more
likely to have pixels landing exactly on these boundaries than a noisy
photo. Fixed by masking off each channel's LSB before computing intensity
everywhere it drives channel selection, and before sampling pixels for the
master key - since embedding only ever changes a channel's LSB, masking it
out makes both computations identical whether read before or after
embedding, for any image. Covered by two regression tests: one using the
exact flat-color image that surfaced this, one using a synthetic image
built entirely from boundary-intensity pixels.

**Security/robustness**
- `SECRET_KEY` no longer falls back to a hardcoded default - the app now
  refuses to start without it, so a missing env var in production is a
  loud failure instead of a silent security hole.
- Fixed asset paths in `index.html` (`../static/...` -> `/static/...`).

**Image size & format support**
- The original frontend only accepted PNG/JPEG/BMP (hardcoded in both the
  HTML `accept` attribute and a JS whitelist) even though the backend
  already handled any format Pillow can decode. The frontend now accepts
  any image type.
- Pillow 10.4.0 (the original pin) has no AVIF support at all, and never
  supports HEIC/HEIF (iPhone's default photo format) without a separate
  plugin. Bumped to Pillow 12.3.0 (native AVIF support) and added
  `pillow-heif` for HEIC/HEIF, registered once at app startup. Tested
  round-trip: PNG, JPEG, BMP, WEBP, TIFF, GIF, AVIF, HEIF - all pass.
- The hardcoded 4-megapixel cover-image limit (sized for a 512MB host) is
  now the configurable `MAX_IMAGE_MEGAPIXELS`, defaulting to 30 - a more
  realistic ceiling for a 12GB VM. Same for the 32MB upload cap, now
  `MAX_UPLOAD_MB` (default 64).
- The same size/format validation that only existed on `/api/hide_message`
  now also applies to `/api/batch_hide` (the original silently skipped it
  for batch uploads).
- PSNR/SSIM metric calculation was switched from float64 to float32,
  roughly halving processing time on large images (a 12MP photo: ~19s ->
  ~14s) with no meaningful precision loss for a quality metric. Deployment
  configs (`gunicorn --timeout`, nginx `proxy_read_timeout`) were raised to
  120s to give large images headroom.

## Supported image formats

Any format Pillow (with `pillow-heif` for HEIC/HEIF) can decode works as a
cover/stego image. Tested and covered by the test suite:

PNG, JPEG, BMP, WEBP, TIFF, GIF, AVIF, HEIC/HEIF

Pillow itself recognizes dozens more (ICO, TGA, PCX, PSD, and others) -
any of those should work too, since the app never restricts by format,
only by decodability. Output is always re-saved as PNG regardless of
input format, since LSB steganography requires a lossless container - a
lossy output format would destroy the hidden bits.

## Project structure

```
stego-app/
├── app/
│   ├── __init__.py            # create_app() factory
│   ├── config.py              # env-driven config + SECRET_KEY validation
│   ├── routes/
│   │   ├── pages.py           # /, /explanation, /demos, /quiz, ...
│   │   └── api.py             # /api/hide_message, /api/extract_message, /api/batch_*
│   ├── core/
│   │   ├── steganography.py   # LSB embedding/extraction + AES (was stegfile.py)
│   │   └── visualization.py   # batch performance graphs
│   ├── templates/
│   │   └── index.html         # main UI
│   └── static/
│       ├── css/styles.css
│       ├── js/script.js
│       ├── pages/             # explanation, demos, flowchart, glossary, quiz, resources, security_guide
│       └── graphs/            # generated at runtime
├── deploy/
│   ├── Procfile                # Heroku-style (kept for reference)
│   ├── render.yaml              # Render.com config (kept for reference)
│   ├── start.sh                  # gunicorn launch script
│   ├── stego.service             # systemd unit for a VPS (e.g. Google Cloud, Oracle Cloud)
│   └── nginx-stego.conf          # nginx reverse proxy config
├── tests/
│   └── test_smoke.py
├── requirements.txt
├── run.py                       # entrypoint (`run:app`)
├── .env.example
└── .gitignore
```

## Running locally

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set SECRET_KEY, e.g.:
python -c "import secrets; print(secrets.token_hex(32))"

export $(grep -v '^#' .env | xargs)   # or use python-dotenv
python run.py
```

Visit `http://localhost:5000`.

## Running in production (gunicorn)

```bash
export SECRET_KEY=...
export STEGO_BASE_DIR=/tmp/stego-data
bash deploy/start.sh
```

## Deploying - Google Cloud "Always Free" e2-micro VM

Render/Railway/Fly free tiers sleep on idle and cold-start on the next
request. For an app that's always on for free, a real VM is the strongest
option - you fully control it, with no idle-based sleep or request-based
billing. **Google Cloud's Always Free e2-micro instance** is a genuinely
free-forever VM (not a trial), and it uses the exact same deployment files
in `deploy/` as any other Linux VM - nothing provider-specific in the
code. (Oracle Cloud's Always Free Ampere A1 VM is a valid alternative
too and works with these same files, but its signup process is
notoriously failure-prone - capacity errors, identity-verification
rejections - so this guide uses Google Cloud instead.)

**Specs and constraints to know upfront:** e2-micro gives you 2 shared
vCPUs and 1GB RAM, with 30GB of disk - only free in the `us-west1`,
`us-central1`, or `us-east1` regions, and only one instance per account.
1GB RAM is tight for this app's heavier dependencies (matplotlib, pandas,
scikit-image); run a single gunicorn worker and consider lowering
`MAX_IMAGE_MEGAPIXELS` (e.g. to 8-10) so large-image processing doesn't
exhaust memory. There's also a 1GB/month free egress cap - fine for
personal/demo use, but heavy traffic could exceed it.

1. **Sign up** at cloud.google.com/free (a card is required for identity
   verification; you won't be charged while staying within Always Free
   limits - Google's verification flow is generally more reliable than
   Oracle's).
2. **Create a VM instance**: Compute Engine → VM Instances → Create
   Instance.
   - Region: `us-central1` (Iowa), `us-west1` (Oregon), or `us-east1`
     (South Carolina) - only these three qualify for the free tier.
   - Machine type: `e2-micro` (General Purpose → E2 series).
   - Boot disk: Ubuntu (22.04 LTS or newer), size ≤30GB, **Standard
     persistent disk** (not SSD/Balanced - those aren't free).
   - Under Firewall, check **"Allow HTTP traffic"** and **"Allow HTTPS
     traffic"** - this is the equivalent of Oracle's security list step,
     done here instead of afterward.
3. **Open the OS-level firewall too** (the GCP checkbox above only opens
   the *network* firewall - Ubuntu's own `ufw` still blocks it by
   default, this is the same gotcha as on Oracle):
   ```bash
   sudo ufw allow 80,443/tcp
   ```
4. **SSH in** - easiest is the "SSH" button next to your instance in the
   GCP Console (opens a browser-based terminal, no key setup needed), or
   use `gcloud compute ssh` from your own machine. Then set up the app:
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip nginx
   git clone <your-repo> stego-app && cd stego-app
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   printf "SECRET_KEY=%s\n" "$(venv/bin/python -c 'import secrets;print(secrets.token_hex(32))')" > .env
   echo "STEGO_BASE_DIR=/tmp/stego-data" >> .env
   echo "MAX_IMAGE_MEGAPIXELS=8" >> .env
   ```
   Note: `.env` for systemd's `EnvironmentFile` needs plain `KEY=VALUE`
   lines - no `export`, no quotes.
5. **Install the systemd service** so gunicorn survives crashes and
   reboots:
   ```bash
   sudo cp deploy/stego.service /etc/systemd/system/stego.service
   # edit User/WorkingDirectory paths in the file to match your setup
   # (the default assumes user "ubuntu" - GCP's Ubuntu images use your
   # Google account username instead, e.g. "your_name")
   sudo systemctl daemon-reload
   sudo systemctl enable --now stego
   sudo systemctl status stego
   ```
6. **Install nginx as a reverse proxy** (public port 80/443 -> internal
   gunicorn on 127.0.0.1:8000), so you can add a free TLS cert later
   without touching the app:
   ```bash
   sudo cp deploy/nginx-stego.conf /etc/nginx/sites-available/stego
   sudo ln -s /etc/nginx/sites-available/stego /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t && sudo systemctl reload nginx
   ```
7. Visit `http://<your-VM-external-IP>/` (shown next to your instance in
   the GCP Console).
8. **Optional**: reserve a static external IP (Console → VPC Network →
   IP addresses - promoting the ephemeral one to static is free as long
   as it stays attached to a running instance), point a free DNS name at
   it, and run `sudo apt install certbot python3-certbot-nginx && sudo
   certbot --nginx` for free HTTPS.

**One thing to be aware of:** unlike Oracle, Google Cloud's Always Free
e2-micro does not reclaim instances for being idle - once it's running,
it stays running regardless of traffic, with no cron-based keepalive
needed.

## Hiding a file instead of a text message

Beyond plain text, you can hide an arbitrary file (PDF, Word doc, Excel
sheet, another image, etc.) inside the cover image:

- **UI**: on the Hide tab, use the "Or Hide a File Instead" upload area. If
  a file is selected there, it replaces the text message - the whole file
  is hidden. On the Extract tab, if a hidden file (rather than text) is
  recovered, a "Download" button appears instead of/alongside the message
  box. The Batch Processing tab has the same file option for Batch Hide
  (one shared file gets hidden in every cover image), and Batch Extract's
  results table shows a per-row download button wherever a file (rather
  than text) was recovered.
- **API**: pass a `payloadFile` upload to `/api/hide_message` or
  `/api/batch_hide` (it takes priority over the `message` field if both
  are given). `/api/extract_message` and `/api/batch_extract` return
  `isFile: true`, `filename`, `fileSize`, and `fileData` (a downloadable
  base64 data URI) when a file - rather than text - was recovered;
  responses are unchanged for ordinary text messages.

Implementation-wise, this required no changes to the LSB/AES/adaptive-
channel algorithm at all (see `app/core/payload.py`): a small file is
packed into a text string (a JSON header with the filename, followed by
its bytes base64-encoded) before being handed to the exact same
`hide_message()` used for plain text, and unpacked back out of whatever
`extract_message()` returns. The same size/capacity limits that apply to
text messages apply here - a large file needs a correspondingly large
cover image.

## Helpful error messages and mode-mismatch auto-detection

Two usability improvements worth knowing about:

**Capacity errors now suggest a fix.** Enhanced/Adaptive mode only uses 2
of 3 color channels per pixel (for better stealth), so it has a third
less capacity than Simple LSB. If your message or file doesn't fit in
Enhanced/Adaptive mode but *would* fit with Simple LSB, the error says so
explicitly - e.g. *"Disabling 'Enhanced Bit Distribution' and 'Adaptive
Channel' would provide ~X bits - enough to fit this."* If even Simple LSB
wouldn't have room, it suggests a larger cover image instead.

**Extraction auto-detects an Enhanced/Adaptive settings mismatch.** If you
hide something with these toggles off and send the image to someone else,
they have no way to know that from the image alone - their own toggles
(whatever they default to) won't match, and extraction would otherwise
just fail with no indication of why. Extraction now automatically retries
with the opposite mode if the first attempt fails, and if that's what
actually works, the response clearly flags it (`modeMismatchDetected`),
the operation log explains what happened, and the UI's checkboxes update
to reflect the settings that actually worked. A genuinely wrong key or
corrupted image still fails normally either way - this only kicks in for
the specific "right key, wrong mode" case.

## API Reference

- `POST /api/generate_key` - generate a new AES-256 key
- `POST /api/hide_message` - hide a message (or file, via `payloadFile`) in a single image
- `POST /api/extract_message` - extract a message (or file) from a stego image
- `POST /api/batch_hide` - hide the same message/file in multiple images (returns a zip)
- `POST /api/batch_extract` - extract messages/files from multiple images
- `POST /api/batch_performance_graphs` - generate PSNR/SSIM/BER/capacity graphs

See the in-app `/explanation`, `/flowchart`, and `/security-guide` pages
for details on the algorithm and its parameters.

## Known limitations (carried over from the original design)

- The "embed key in image" feature derives its obfuscation key from a
  handful of fixed pixel coordinates in the stego image - this is
  intentionally lightweight, not cryptographically strong. Treat it as
  convenience, not security; prefer sharing the key out-of-band for
  anything sensitive.
- Steganography hides data, it does not by itself guarantee
  confidentiality - use AES (on by default) for that.
- Image size is capped at 30 megapixels by default (configurable via
  `MAX_IMAGE_MEGAPIXELS`) to keep memory and processing time predictable.
  Any format Pillow can decode is accepted (PNG, JPEG, BMP, WEBP, TIFF,
  GIF, ...) - output is always saved as PNG, since LSB steganography
  requires a lossless format.
- Processing time scales with image size, dominated by the PSNR/SSIM
  quality-metric calculation (not the embedding itself, which is fast).
  As a rough guide: a 12-megapixel photo takes roughly 10-15 seconds to
  hide a message; the deployment configs set gunicorn's timeout to 120s
  to leave headroom.

---

**Note**: for educational and research purposes. Follow local laws and
regulations regarding steganography and encryption where you deploy this.
