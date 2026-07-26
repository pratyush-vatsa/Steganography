"""
File payload packing/unpacking.

This is the "Tier 1" extension discussed previously: hiding an arbitrary
file (PDF, Word doc, Excel sheet, another image, etc.) inside a cover
image, using the exact same embedding pipeline that already hides text
messages - no changes to the LSB/AES/adaptive-channel algorithm itself.

How it works: the algorithm only ever cares about the "message" string it's
given - it doesn't know or care whether that string is human-readable text.
So a file is packed into a single text string (a small JSON header
describing the original filename, followed by the file's bytes encoded as
base64) and that string is passed through hide_message() completely
unchanged. On extraction, if the recovered message starts with this
module's marker, it's unpacked back into the original file bytes and
filename; otherwise it's treated as an ordinary text message exactly as
before, so nothing here is a breaking change.

Why base64 and not the raw bytes directly: the existing pipeline runs
AES/error-correction on the message via message.encode('utf-8') /
.decode('utf-8'). Arbitrary binary file bytes are not, in general, valid
UTF-8, so encoding/decoding them directly would silently corrupt data via
Python's UTF-8 replacement-character handling. Base64 output is pure
ASCII, which round-trips through UTF-8 perfectly, at the cost of ~33%
size overhead - the same tradeoff the app already makes for the AES
ciphertext and the embedded key.
"""
import base64
import json

MARKER = "STEGOFILE_V1:"


def pack_file_payload(filename, data):
    """
    Build a single text string encoding a file's name and bytes, suitable
    for passing directly as the `message` argument to hide_message().

    Args:
        filename: original filename (used only for display/download on
            extraction - never used as a path, so no path traversal risk).
        data: raw file bytes.

    Returns:
        A packed string starting with MARKER.
    """
    header = json.dumps({"filename": filename, "size": len(data)})
    encoded = base64.b64encode(data).decode("ascii")
    return f"{MARKER}{header}\n{encoded}"


def unpack_file_payload(message):
    """
    Attempt to unpack a message produced by pack_file_payload().

    Returns:
        A dict {"filename": str, "size": int|None, "data": bytes} if
        `message` is a packed file payload, otherwise None (meaning it's
        an ordinary text message - callers should fall back to treating
        it as plain text).
    """
    if not message or not message.startswith(MARKER):
        return None
    rest = message[len(MARKER):]
    try:
        header_json, encoded = rest.split("\n", 1)
        meta = json.loads(header_json)
        data = base64.b64decode(encoded)
        filename = meta.get("filename") or "extracted_file"
        return {"filename": filename, "size": meta.get("size"), "data": data}
    except Exception:
        # Any parsing failure just means this isn't a (recognizable)
        # packed file payload - treat the message as plain text instead
        # of raising, since a corrupted/foreign message shouldn't crash
        # extraction.
        return None
