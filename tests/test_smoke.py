"""
Basic smoke tests: confirms the app factory boots and the main routes
respond. Run with: pytest
"""
import base64
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-only-key-do-not-use-in-production")

from app import create_app  # noqa: E402


def make_client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_index_page_loads():
    client = make_client()
    resp = client.get("/")
    assert resp.status_code == 200


def test_info_pages_load():
    client = make_client()
    for path in ["/explanation", "/demos", "/flowchart", "/resources", "/quiz", "/glossary", "/security-guide"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"


def test_generate_key_endpoint():
    client = make_client()
    resp = client.post("/api/generate_key")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "key" in data
    assert len(data["key"]) == 64  # 32 bytes as hex


def test_hide_message_requires_key():
    client = make_client()
    resp = client.post("/api/hide_message", data={"message": "hi"})
    assert resp.status_code == 400


def _make_image_bytes(fmt, size=(64, 64)):
    from PIL import Image
    img = Image.new("RGB", size, color=(120, 60, 200))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


@pytest.mark.parametrize("fmt,filename", [
    ("PNG", "cover.png"),
    ("JPEG", "cover.jpg"),
    ("BMP", "cover.bmp"),
    ("WEBP", "cover.webp"),
    ("TIFF", "cover.tiff"),
    ("GIF", "cover.gif"),
    ("AVIF", "cover.avif"),
    ("HEIF", "cover.heif"),
])
def test_hide_and_extract_roundtrip_across_formats(fmt, filename):
    """Any Pillow-decodable format should hide/extract correctly - the
    backend never restricted formats, only the old frontend did."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    message = "Round trip check!"

    buf = _make_image_bytes(fmt)
    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (buf, filename),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success"), f"{fmt} hide failed: {data.get('error')}"

    out_bytes = base64.b64decode(data["outputImage"].split(",", 1)[1])
    resp2 = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data2 = resp2.get_json()
    assert data2.get("success"), f"{fmt} extract failed: {data2.get('message')}"
    assert data2.get("message") == message


def test_oversized_image_is_rejected():
    client = make_client()
    from app import create_app as _create_app  # already imported app instance via client.application
    client.application.config["MAX_IMAGE_MEGAPIXELS"] = 0.001  # ~1000 px, so a 64x64 image trips it

    buf = _make_image_bytes("PNG")
    resp = client.post(
        "/api/hide_message",
        data={"coverImage": (buf, "cover.png"), "message": "hi", "key": "0" * 64},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 413
    assert "too large" in resp.get_json()["error"].lower()


def test_image_megapixel_limit_is_configurable():
    # Config values are read at app-creation time from the environment, so
    # this confirms the app instance's config can be overridden per
    # deployment - not that re-setting os.environ retroactively changes an
    # already-created app (it doesn't, by design).
    app = create_app()
    assert "MAX_IMAGE_MEGAPIXELS" in app.config
    app.config["MAX_IMAGE_MEGAPIXELS"] = 0.5
    assert app.config["MAX_IMAGE_MEGAPIXELS"] == 0.5


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def test_embedded_key_extraction_on_flat_color_illustration():
    """
    Regression test for a real reported failure: enhanced/adaptive mode
    picks embedding channels based on each pixel's average intensity
    (<85 -> R,G; 85-170 -> G,B; >170 -> R,B). Embedding a bit changes that
    same pixel's intensity by up to ~1, which - without masking off the
    LSB before computing intensity - can push a pixel sitting right at the
    85 or 170 boundary across it, so extraction picks a different channel
    pair than embedding used and corrupts the payload.

    Flat-color illustrations (large areas of near-identical color) are far
    more likely than noisy photos to have pixels sitting exactly at these
    boundaries, which is why this failed on a specific image and not
    others. This uses the exact image that first surfaced the bug, with
    the exact settings (adaptive channel + embedded key, no manually
    supplied key at extraction time) that triggered it.
    """
    client = make_client()
    fixture_path = os.path.join(FIXTURES_DIR, "beach_illustration.png")
    with open(fixture_path, "rb") as f:
        img_bytes = f.read()

    key = client.post("/api/generate_key").get_json()["key"]
    message = "Secret test message for the beach image!"

    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (io.BytesIO(img_bytes), "cover.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
            "embedKey": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success"), f"hide failed: {data.get('error')}"

    out_bytes = base64.b64decode(data["outputImage"].split(",", 1)[1])

    # Extract WITHOUT supplying a key - relies entirely on the embedded key
    resp2 = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
            "extractKey": "true",
        },
        content_type="multipart/form-data",
    )
    data2 = resp2.get_json()
    assert data2.get("success"), f"extract failed: {data2.get('message')}"
    assert data2.get("message") == message
    assert data2.get("extractedKey") == key


def test_adaptive_channel_selection_survives_boundary_pixels():
    """
    Synthetic worst case: an image built entirely from pixels whose
    intensity sits exactly on the 85/170 channel-selection boundaries, so
    every single embedded bit is at risk of the mismatch described above.
    If this passes, the fix generalizes beyond the one reported image.
    """
    from PIL import Image
    import numpy as np

    client = make_client()
    h, w = 64, 64
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    # Alternate rows between intensity exactly 85 and exactly 170
    arr[0::2] = [85, 85, 85]
    arr[1::2] = [170, 170, 170]
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    key = client.post("/api/generate_key").get_json()["key"]
    message = "Boundary stress test"

    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (buf, "boundary.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success"), f"hide failed: {data.get('error')}"

    out_bytes = base64.b64decode(data["outputImage"].split(",", 1)[1])
    resp2 = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data2 = resp2.get_json()
    assert data2.get("success"), f"extract failed: {data2.get('message')}"
    assert data2.get("message") == message


def test_hide_and_extract_file_payload_roundtrip():
    """
    Tier 1 feature: hiding an arbitrary file (not text) as the payload.
    Uses a deliberately adversarial byte sequence (values >127) that would
    silently corrupt under a naive UTF-8 char-mapping approach, to prove
    the base64-wrapping in app/core/payload.py actually protects against
    that pitfall.
    """
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]

    file_bytes = bytes([0, 1, 2, 200, 201, 255, 254, 128, 127, 65, 66, 67]) * 20
    cover_buf = _make_image_bytes("PNG", size=(300, 300))

    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (cover_buf, "cover.png"),
            "payloadFile": (io.BytesIO(file_bytes), "secret_report.pdf"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success"), f"hide failed: {data.get('error')}"
    assert data.get("isFilePayload") is True
    assert data.get("payloadFilename") == "secret_report.pdf"

    out_bytes = base64.b64decode(data["outputImage"].split(",", 1)[1])
    resp2 = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data2 = resp2.get_json()
    assert data2.get("success"), f"extract failed: {data2.get('message')}"
    assert data2.get("isFile") is True
    assert data2.get("filename") == "secret_report.pdf"

    recovered = base64.b64decode(data2["fileData"].split(",", 1)[1])
    assert recovered == file_bytes


def test_plain_text_message_unaffected_by_file_payload_feature():
    """Backward compatibility: ordinary text messages must behave exactly
    as before - no isFile/isFilePayload noise in the response."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    message = "Just an ordinary text message"

    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (_make_image_bytes("PNG"), "cover.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success")
    assert data.get("isFilePayload") is False

    out_bytes = base64.b64decode(data["outputImage"].split(",", 1)[1])
    resp2 = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data2 = resp2.get_json()
    assert data2.get("success")
    assert data2.get("message") == message
    assert not data2.get("isFile")


def test_batch_hide_extract_with_shared_file_payload():
    """The same file payload, shared across a batch of cover images."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    file_bytes = b"Shared batch file content \x00\x01\xff\xfe" * 10

    resp = client.post(
        "/api/batch_hide",
        data={
            "coverImages": [
                (_make_image_bytes("PNG"), "a.png"),
                (_make_image_bytes("PNG"), "b.png"),
            ],
            "payloadFile": (io.BytesIO(file_bytes), "budget.xlsx"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success")
    assert all(r.get("success") for r in data.get("results", []))

    import zipfile

    zip_bytes = base64.b64decode(data["zipFile"].split(",", 1)[1])
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    stego_names = [n for n in zf.namelist() if n.endswith("_stego.png")]
    assert len(stego_names) == 2

    resp2 = client.post(
        "/api/batch_extract",
        data={
            "stegoImages": [(io.BytesIO(zf.read(n)), n) for n in stego_names],
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data2 = resp2.get_json()
    assert data2.get("success")
    for r in data2.get("results", []):
        assert r.get("success")
        assert r.get("isFile") is True
        recovered = base64.b64decode(r["fileData"].split(",", 1)[1])
        assert recovered == file_bytes


def test_capacity_error_suggests_simple_lsb_when_it_would_fit():
    """When Enhanced/Adaptive mode doesn't have room but Simple LSB would,
    the error should say so explicitly instead of just "too large"."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    # A message sized to fit in Simple LSB (3 bits/px) but not Enhanced (2 bits/px)
    # on a small test image.
    message = "A" * 900
    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (_make_image_bytes("PNG", size=(64, 64)), "cover.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success") is False
    assert "Disabling 'Enhanced Bit Distribution'" in data.get("error", "")


def test_capacity_error_suggests_larger_image_when_simple_also_insufficient():
    """When even Simple LSB wouldn't fit, the suggestion should be a bigger
    image/shorter message, not the (useless) Enhanced/Adaptive toggle tip."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    message = "A" * 50000  # far too large for a 64x64 image in any mode
    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (_make_image_bytes("PNG", size=(64, 64)), "cover.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    data = resp.get_json()
    assert data.get("success") is False
    assert "Disabling 'Enhanced Bit Distribution'" not in data.get("error", "")
    assert "larger cover image" in data.get("error", "")


def test_extract_auto_detects_mode_mismatch():
    """Regression test for the reported cross-user scenario: person A hides
    with Simple LSB, person B (who doesn't know that) tries to extract with
    Enhanced/Adaptive settings. Extraction should still succeed, and the
    response should clearly flag that a mismatch was detected and corrected."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    message = "Cross-user mode mismatch regression test"

    hide_resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (_make_image_bytes("PNG", size=(300, 300)), "cover.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "false",
            "adaptiveChannel": "false",
        },
        content_type="multipart/form-data",
    )
    hide_data = hide_resp.get_json()
    assert hide_data.get("success")
    out_bytes = base64.b64decode(hide_data["outputImage"].split(",", 1)[1])

    # "Person B" requests Enhanced/Adaptive - the wrong mode for this image.
    extract_resp = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    extract_data = extract_resp.get_json()
    assert extract_data.get("success") is True
    assert extract_data.get("modeMismatchDetected") is True
    assert extract_data.get("actualEnhancedBit") is False
    assert extract_data.get("actualAdaptiveChannel") is False
    assert extract_data.get("message") == message


def test_wrong_key_does_not_produce_false_positive_mode_mismatch():
    """Safety check: the mode-mismatch auto-retry must not mask a genuinely
    wrong key as a successful mode-corrected extraction."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]
    wrong_key = client.post("/api/generate_key").get_json()["key"]
    message = "Should not be recoverable with the wrong key"

    hide_resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (_make_image_bytes("PNG", size=(300, 300)), "cover.png"),
            "message": message,
            "key": key,
            "useAES": "true",
            "enhancedBit": "false",
            "adaptiveChannel": "false",
        },
        content_type="multipart/form-data",
    )
    out_bytes = base64.b64decode(hide_resp.get_json()["outputImage"].split(",", 1)[1])

    extract_resp = client.post(
        "/api/extract_message",
        data={
            "stegoImage": (io.BytesIO(out_bytes), "stego.png"),
            "key": wrong_key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    extract_data = extract_resp.get_json()
    assert extract_data.get("success") is False
    assert not extract_data.get("modeMismatchDetected")


def test_metrics_module_sanity():
    """
    Unit tests for the pure NumPy/SciPy PSNR/SSIM implementation that
    replaced scikit-image (see app/core/metrics.py). Not a comparison
    against scikit-image (that dependency is intentionally gone) - these
    check the well-known mathematical properties any correct PSNR/SSIM
    implementation must satisfy.
    """
    import numpy as np
    from app.core.metrics import peak_signal_noise_ratio, structural_similarity

    rng = np.random.default_rng(42)
    a = (rng.random((100, 100, 3)) * 255).astype(np.float64)

    # Identical images: PSNR is infinite, SSIM is exactly 1.
    assert peak_signal_noise_ratio(a, a.copy()) == float("inf")
    assert structural_similarity(a, a.copy(), channel_axis=2) == 1.0

    # Small perturbation: PSNR should be high but finite, SSIM very close to 1.
    b = a.copy()
    b[0, 0, 0] = min(255, b[0, 0, 0] + 1)
    psnr_val = peak_signal_noise_ratio(a, b)
    ssim_val = structural_similarity(a, b, channel_axis=2)
    assert 0 < psnr_val < float("inf")
    assert 0.9 < ssim_val <= 1.0

    # Large perturbation: both metrics should drop noticeably.
    c = np.clip(a + rng.normal(0, 40, a.shape), 0, 255)
    psnr_val2 = peak_signal_noise_ratio(a, c)
    ssim_val2 = structural_similarity(a, c, channel_axis=2)
    assert psnr_val2 < psnr_val
    assert ssim_val2 < ssim_val


def test_batch_graphs_generation_without_pandas():
    """Regression test for the pandas -> plain-Python rewrite in
    visualization.py: batch hide, then generate graphs from the results."""
    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]

    resp = client.post(
        "/api/batch_hide",
        data={
            "coverImages": [
                (_make_image_bytes("PNG", size=(150, 150)), "a.png"),
                (_make_image_bytes("PNG", size=(150, 150)), "b.png"),
            ],
            "message": "Graph generation regression test",
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    hide_data = resp.get_json()
    assert hide_data.get("success")

    results_payload = [
        {
            "filename": r["filename"],
            "psnr": r["psnr"],
            "ssim": r["ssim"],
            "ber": r["ber"],
            "capacity": r["capacity"],
            "file_size": r["file_size"],
        }
        for r in hide_data["results"]
    ]
    resp2 = client.post("/api/batch_performance_graphs", json={"results": results_payload})
    data2 = resp2.get_json()
    assert data2.get("success")
    assert len(data2.get("graphs", [])) == 3


def test_metrics_memory_stays_bounded_on_large_image():
    """
    Regression test for a real production incident: the original
    metrics.py used float64 with no explicit cleanup, which measured at
    ~1.6GB peak RSS on a realistic 12-megapixel photo - enough to OOM-kill
    the process on a small (1GB RAM) host, breaking hide_message()
    entirely for any real-world-sized photo. This pins the fix (float32 +
    explicit intermediate cleanup) to a hard ceiling well under what a
    small VM can provide, so a future change can't silently reintroduce
    the blowup.
    """
    import resource
    import numpy as np
    from app.core import metrics

    rng = np.random.default_rng(42)
    img = (rng.random((3000, 4000, 3)) * 255).astype(np.uint8)
    stego = img.copy()
    stego[:, :, 0] = stego[:, :, 0] ^ 1

    mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    metrics.peak_signal_noise_ratio(img, stego, data_range=255)
    metrics.structural_similarity(img, stego, channel_axis=2, data_range=255)
    mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Generous ceiling (not a tight bound) - just needs to catch a
    # regression back toward gigabyte-scale usage, not chase the exact
    # current number.
    mem_used_mb = (mem_after - mem_before) / 1024
    assert mem_used_mb < 700, (
        f"Metrics calculation used {mem_used_mb:.0f}MB above baseline for a "
        f"12-megapixel image - expected well under 700MB. This likely means "
        f"the float32/explicit-cleanup fix in metrics.py regressed."
    )


def test_metrics_matches_scikit_image_closely():
    """Correctness check: our pure NumPy/SciPy PSNR/SSIM must stay
    numerically indistinguishable from scikit-image's real implementation,
    since the whole point is a drop-in replacement."""
    pytest.importorskip("skimage")
    import numpy as np
    from skimage.metrics import peak_signal_noise_ratio as sk_psnr, structural_similarity as sk_ssim
    from app.core import metrics

    rng = np.random.default_rng(7)
    img = (rng.random((256, 256, 3)) * 255).astype(np.uint8)
    stego = img.copy()
    stego[10:20, 10:20, 1] ^= 1

    our_psnr = metrics.peak_signal_noise_ratio(img, stego, data_range=255)
    their_psnr = sk_psnr(img, stego, data_range=255)
    assert abs(our_psnr - their_psnr) < 0.01

    our_ssim = metrics.structural_similarity(img, stego, channel_axis=2, data_range=255)
    their_ssim = sk_ssim(img, stego, channel_axis=2, data_range=255)
    assert abs(our_ssim - their_ssim) < 0.001


def test_hide_memory_stays_within_small_vm_budget():
    """
    Regression test for a real production incident: the kernel OOM-killed
    the gunicorn worker mid-request on a 1GB VM during hide_message,
    traced to the PSNR/SSIM calculation's peak memory footprint. Measured
    directly on this codebase: roughly 63MB baseline + 78MB per megapixel
    of cover image for the full hide_message() request (not just the
    metrics functions in isolation - see
    test_metrics_memory_stays_bounded_on_large_image for that).

    Uses delta (before/after), matching the proven methodology of the
    existing metrics-only test above, rather than absolute peak RSS -
    absolute peak measured via a nested subprocess turned out to include
    unrelated baseline noise and gave inconsistent numbers between runs.
    """
    import resource
    import io
    import numpy as np
    from PIL import Image

    client = make_client()
    key = client.post("/api/generate_key").get_json()["key"]

    arr = (np.random.default_rng(11).random((1500, 2000, 3)) * 255).astype(np.uint8)  # 3 megapixels
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)

    mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    resp = client.post(
        "/api/hide_message",
        data={
            "coverImage": (buf, "cover.jpg"),
            "message": "Regression test message",
            "key": key,
            "useAES": "true",
            "enhancedBit": "true",
            "adaptiveChannel": "true",
        },
        content_type="multipart/form-data",
    )
    mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    assert resp.get_json().get("success"), resp.get_json()

    mem_used_mb = (mem_after - mem_before) / 1024

    # Measured ~250-300MB above baseline for this exact 3MP image when this
    # test was written. Generous ceiling, not a tight bound - a real
    # regression (e.g. a float64 reintroduction) would blow well past this.
    assert mem_used_mb < 500, (
        f"hide_message used {mem_used_mb:.0f}MB above baseline for a 3MP "
        f"image - expected well under 500MB. This is the same class of "
        f"regression that caused OOM kills in production on a 1GB VM - "
        f"check for a new float64 conversion or a missing `del` in "
        f"app/core/metrics.py or app/core/steganography.py."
    )
