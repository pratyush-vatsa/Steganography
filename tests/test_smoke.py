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
