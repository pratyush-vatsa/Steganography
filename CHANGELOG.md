# Changelog

All notable changes to this project are documented here. This project started
as a single-file Flask prototype (`Stego-TESTING-11` / `app12.py`) and was
restructured and hardened into its current form.

## [Unreleased]

### Added
- **Hide an arbitrary file instead of a text message.** PDF, Word docs, Excel
  sheets, other images, etc. can now be hidden the same way a text message
  is - see `app/core/payload.py`. No changes to the LSB/AES/adaptive-channel
  algorithm were needed: a file is packed into a text string (a JSON header
  with the filename, followed by its bytes base64-encoded) before being
  handed to the existing `hide_message()`, and unpacked back out of whatever
  `extract_message()` returns. Available in the UI (Hide, Extract, and Batch
  tabs) and via the API (`payloadFile` field on `/api/hide_message` and
  `/api/batch_hide`; `isFile`/`filename`/`fileData` in extraction responses).
- **Capacity errors now suggest a fix.** Enhanced/Adaptive mode uses 2 of 3
  color channels per pixel, a third less capacity than Simple LSB. If a
  message/file doesn't fit in Enhanced/Adaptive mode but would fit with
  Simple LSB, the error explains that explicitly. If even Simple LSB
  wouldn't have room, it suggests a larger cover image instead.
- **Extraction auto-detects an Enhanced/Adaptive settings mismatch.** These
  two toggles aren't stored in the image - if hidden with one setting and
  extracted with another (e.g. by a different person who doesn't know what
  was used), extraction used to just fail. It now automatically retries with
  the opposite mode, and if that's what works, the response flags it
  (`modeMismatchDetected`), the operation log explains what happened, and the
  UI's checkboxes update to reflect the settings that actually worked. A
  genuinely wrong key or corrupted image still fails normally either way.
- Full Linear-inspired UI redesign: layered charcoal surfaces, a single
  accent color, refined typography (Inter), softer shadows/borders, and
  subtle motion - CSS-only, no HTML/JS structure changes, so no functionality
  was touched.
- Minimal `tests/` smoke-test suite (pytest) - 23 tests covering routes,
  format/size handling, both bugfixes below, and the file-payload feature.

### Changed
- Reorganized into a standard Flask "application factory + blueprints"
  layout instead of one large `app12.py`: `app12.py` -> `app/routes/{pages,
  api}.py`, `stegfile.py` -> `app/core/steganography.py`, `templates/
  index1.html` -> `app/templates/index.html`. Deployment configs moved into
  `deploy/`.
- Any image format Pillow can decode is now accepted, not just PNG/JPEG/BMP -
  the original frontend hardcoded that whitelist even though the backend
  never needed it. Bumped Pillow to 12.3.0 (native AVIF support) and added
  `pillow-heif` for HEIC/HEIF (the default photo format on iPhones).
- The hardcoded 4-megapixel cover-image limit (sized for a 512MB host) is
  now the configurable `MAX_IMAGE_MEGAPIXELS` (default 30). Same for the
  32MB upload cap, now `MAX_UPLOAD_MB` (default 64). The same validation
  that only existed on `/api/hide_message` now also applies to
  `/api/batch_hide`.
- PSNR/SSIM metric calculation switched from float64 to float32, roughly
  halving processing time on large images with no meaningful precision loss.
- `SECRET_KEY` no longer falls back to a hardcoded default - the app refuses
  to start without it.

### Fixed
- **Header/payload boundary bug.** `extract_message()` speculatively reads
  72 raw bits up front (enough for the largest possible header, in case a
  key is embedded). When no key is embedded, the real header is only 40
  bits - the original code discarded bits 40-71 as unused padding, but they
  were already the first 32 bits of the real message. This silently dropped
  32 bits from the front of every message hidden with `embedKey` off, and
  shifted everything after it (also breaking AES decryption, since the
  corrupted bytes no longer formed a valid block). Present in the original
  app, not introduced by the restructuring - verified against the
  unmodified original code before being fixed.
- **Adaptive channel-selection bug.** Enhanced/Adaptive mode picks which 2
  of 3 RGB channels to embed into based on a pixel's average intensity
  (`<85` -> R,G; `85-170` -> G,B; `>170` -> R,B). Embedding a bit changes
  that pixel's intensity by up to ~1 (from flipping a channel's LSB) -
  without masking that LSB out before computing intensity, a pixel whose
  *original* intensity sits right at 85 or 170 could cross the threshold
  once embedded, so extraction (recomputing intensity from the now-modified
  pixel) would pick a different channel pair than embedding used, corrupting
  the payload. Also affected the "embed key in image" feature's master-key
  derivation, which samples pixel `(0,0)` - the very first pixel embedding
  touches. Surfaced more often on flat-color illustrations (large
  near-identical-color regions) than noisy photos. Fixed by masking off
  each channel's LSB before computing intensity everywhere it drives channel
  selection or master-key sampling.
- Fixed broken relative asset paths in the main template (`../static/...`
  -> `/static/...`).
