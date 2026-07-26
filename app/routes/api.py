"""
JSON API endpoints: key generation, single hide/extract, batch hide/extract,
and batch performance graph generation.

Logic is unchanged from the original app12.py - only the module layout,
imports, and a couple of small hardening tweaks (see steganography.py /
config.py) have changed.
"""
import os
import base64
import io
import mimetypes
import shutil
import tempfile
import traceback
import zipfile
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename

from ..core import steganography as stegfile
from ..core import visualization
from ..core.payload import pack_file_payload, unpack_file_payload

api_bp = Blueprint("api", __name__)


def _temp_dir():
    return current_app.config["TEMP_BASE_DIR"]


def _guess_mimetype(filename):
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


@api_bp.route("/generate_key", methods=["POST"])
def generate_key():
    try:
        return jsonify({"key": stegfile.generate_key()})
    except Exception as e:
        current_app.logger.error(f"Error generating key: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/hide_message", methods=["POST"])
def hide_message():
    cover_path, output_path, temp_files_to_clean = None, None, []
    try:
        if "coverImage" not in request.files:
            return jsonify({"success": False, "error": "Cover image is missing"}), 400
        cover_file = request.files["coverImage"]
        if cover_file.filename == "":
            return jsonify({"success": False, "error": "No cover image selected"}), 400

        # Image size validation to prevent memory overload on the host.
        # Limit is configurable (MAX_IMAGE_MEGAPIXELS) - see app/config.py.
        from PIL import Image, UnidentifiedImageError

        max_pixels = int(current_app.config["MAX_IMAGE_MEGAPIXELS"] * 1_000_000)
        try:
            with Image.open(cover_file) as img:
                width, height = img.size
                if width * height > max_pixels:
                    limit_mp = current_app.config["MAX_IMAGE_MEGAPIXELS"]
                    error_msg = (
                        f"Image too large ({width}x{height} = {width * height / 1_000_000:.1f}MP). "
                        f"This server's limit is {limit_mp:g} megapixels."
                    )
                    current_app.logger.warning(error_msg)
                    return jsonify({"success": False, "error": error_msg}), 413
            cover_file.seek(0)
        except UnidentifiedImageError:
            current_app.logger.warning("Uploaded file is not a valid image.")
            return jsonify(
                {"success": False, "error": "Invalid or corrupt image file. Please upload a valid image."}
            ), 400
        except Exception as img_err:
            current_app.logger.error(f"Error validating image size: {img_err}")
            return jsonify({"success": False, "error": f"Could not read image file: {img_err}"}), 400

        _, ext = os.path.splitext(secure_filename(cover_file.filename))
        fd, cover_path = tempfile.mkstemp(suffix=ext, dir=_temp_dir())
        os.close(fd)
        cover_file.save(cover_path)
        temp_files_to_clean.append(cover_path)
        fd, output_path = tempfile.mkstemp(suffix=".png", dir=_temp_dir())
        os.close(fd)
        temp_files_to_clean.append(output_path)

        data = request.form
        message, key = data.get("message", ""), data.get("key")
        if not key:
            return jsonify({"success": False, "error": "Encryption key is required"}), 400

        # --- Optional file payload: hide an arbitrary file instead of text ---
        # If a file is provided, it takes priority over the `message` field.
        payload_filename = None
        if "payloadFile" in request.files and request.files["payloadFile"].filename:
            payload_file = request.files["payloadFile"]
            payload_bytes = payload_file.read()
            payload_filename = secure_filename(payload_file.filename) or "payload"
            message = pack_file_payload(payload_filename, payload_bytes)

        if not message:
            return jsonify({"success": False, "error": "A message or a file to hide is required"}), 400

        result = stegfile.hide_message(
            cover_path,
            output_path,
            message,
            key,
            use_aes=data.get("useAES") == "true",
            enhanced_bit=data.get("enhancedBit") == "true",
            adaptive_channel=data.get("adaptiveChannel") == "true",
            error_correction=data.get("errorCorrection") == "true",
            embed_key=data.get("embedKey") == "true",
        )
        if "psnr" not in result:
            return jsonify({"success": False, "error": result.get("message", "Hiding process failed.")})

        with open(output_path, "rb") as f:
            output_image_base64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify(
            {
                "success": True,
                "outputImage": f"data:image/png;base64,{output_image_base64}",
                "keyContent": key,
                "metrics": result,
                "encryptedData": result.get("encrypted_message", ""),
                "encryptedKey": result.get("encrypted_key", ""),
                "isFilePayload": payload_filename is not None,
                "payloadFilename": payload_filename,
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error in hide_message: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Hiding failed: {e}"}), 500
    finally:
        for f_path in temp_files_to_clean:
            if f_path and os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except OSError as e:
                    current_app.logger.warning(f"Failed to clean up temp file {f_path}: {e}")


@api_bp.route("/extract_message", methods=["POST"])
def extract_message():
    stego_path, temp_files_to_clean = None, []
    try:
        if "stegoImage" not in request.files:
            return jsonify({"success": False, "error": "Stego image is missing"}), 400
        stego_file = request.files["stegoImage"]
        if stego_file.filename == "":
            return jsonify({"success": False, "error": "No stego image selected"}), 400

        _, ext = os.path.splitext(secure_filename(stego_file.filename))
        fd, stego_path = tempfile.mkstemp(suffix=ext, dir=_temp_dir())
        os.close(fd)
        stego_file.save(stego_path)
        temp_files_to_clean.append(stego_path)

        data = request.form
        requested_enhanced = data.get("enhancedBit") == "true"
        requested_adaptive = data.get("adaptiveChannel") == "true"
        key = data.get("key") or None
        extract_key_flag = data.get("extractKey") == "true"

        result = stegfile.extract_message(
            stego_path,
            key=key,
            use_aes=data.get("useAES") == "true",
            enhanced_bit=requested_enhanced,
            adaptive_channel=requested_adaptive,
            return_raw=True,
            extract_key=extract_key_flag,
        )
        is_error = result.get("message", "").startswith("ERROR:")

        # --- Mode-mismatch auto-detection ---
        # Enhanced/Adaptive mode picks embedding channels differently from
        # Simple LSB - if the person who hid the data used different
        # settings than whoever is extracting, the header marker won't be
        # recognized and extraction fails, with no indication of *why*.
        # There are only two distinct behaviors (both toggles on together,
        # or not), so on failure it's cheap and safe to retry with the
        # opposite mode: a real mismatch will now succeed cleanly (the
        # header marker check that fails first is a structural check, not
        # just a cryptographic one, so this works whether or not AES is
        # in use); a genuinely wrong key/corrupt image will still fail
        # with the same error either way.
        mode_mismatch_detected = False
        if is_error:
            fallback_enhanced = not (requested_enhanced and requested_adaptive)
            fallback_result = stegfile.extract_message(
                stego_path,
                key=key,
                use_aes=data.get("useAES") == "true",
                enhanced_bit=fallback_enhanced,
                adaptive_channel=fallback_enhanced,
                return_raw=True,
                extract_key=extract_key_flag,
            )
            if not fallback_result.get("message", "").startswith("ERROR:"):
                result = fallback_result
                is_error = False
                mode_mismatch_detected = True
                requested_enhanced, requested_adaptive = fallback_enhanced, fallback_enhanced

        response = {
            "success": not is_error,
            "message": result.get("message", ""),
            "rawData": result.get("raw_data", ""),
            "extractedKey": result.get("extracted_key", ""),
            "rawKeyData": result.get("raw_key_data", ""),
        }

        if mode_mismatch_detected:
            response.update(
                {
                    "modeMismatchDetected": True,
                    "actualEnhancedBit": requested_enhanced,
                    "actualAdaptiveChannel": requested_adaptive,
                }
            )

        # --- Optional file payload: was a file hidden instead of text? ---
        if not is_error:
            unpacked = unpack_file_payload(result.get("message", ""))
            if unpacked is not None:
                file_b64 = base64.b64encode(unpacked["data"]).decode("utf-8")
                mimetype = _guess_mimetype(unpacked["filename"])
                response.update(
                    {
                        "isFile": True,
                        "filename": unpacked["filename"],
                        "fileSize": len(unpacked["data"]),
                        "fileData": f"data:{mimetype};base64,{file_b64}",
                        # Replace the raw packed string with a friendly note -
                        # the packed JSON+base64 text isn't useful to display.
                        "message": f"[File: {unpacked['filename']}, {len(unpacked['data'])} bytes - use the download button]",
                    }
                )

        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error in extract_message: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Extraction failed: {e}"}), 500
    finally:
        for f_path in temp_files_to_clean:
            if f_path and os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except OSError as e:
                    current_app.logger.warning(f"Failed to clean up temp file {f_path}: {e}")


@api_bp.route("/batch_hide", methods=["POST"])
def batch_hide():
    results = []
    batch_id = f"batch_hide_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    batch_output_dir = os.path.join(_temp_dir(), batch_id)
    os.makedirs(batch_output_dir)

    try:
        data = request.form
        message, key = data.get("message", ""), data.get("key")
        if not key:
            return jsonify({"success": False, "error": "Encryption key is required"}), 400

        # Optional shared file payload - same file hidden in every image
        # in the batch, symmetric to how `message` is already shared.
        if "payloadFile" in request.files and request.files["payloadFile"].filename:
            payload_file = request.files["payloadFile"]
            payload_bytes = payload_file.read()
            payload_filename = secure_filename(payload_file.filename) or "payload"
            message = pack_file_payload(payload_filename, payload_bytes)

        if not message:
            return jsonify({"success": False, "error": "A message or a file to hide is required"}), 400

        cover_files = request.files.getlist("coverImages")
        if not cover_files:
            return jsonify({"success": False, "error": "No cover images provided"}), 400

        param_map = {
            "useAES": "use_aes",
            "enhancedBit": "enhanced_bit",
            "adaptiveChannel": "adaptive_channel",
            "errorCorrection": "error_correction",
            "embedKey": "embed_key",
        }
        steg_options = {param_map[k]: (v == "true") for k, v in data.items() if k in param_map}

        from PIL import Image, UnidentifiedImageError

        max_pixels = int(current_app.config["MAX_IMAGE_MEGAPIXELS"] * 1_000_000)

        for cover_file in cover_files:
            original_filename = secure_filename(cover_file.filename)
            file_result = {"filename": original_filename, "success": False}

            # Same size/validity check as the single-image endpoint - the
            # original code only validated this on /api/hide_message,
            # silently skipping it for batch uploads.
            try:
                with Image.open(cover_file) as img:
                    width, height = img.size
                    if width * height > max_pixels:
                        limit_mp = current_app.config["MAX_IMAGE_MEGAPIXELS"]
                        file_result["error"] = (
                            f"Image too large ({width}x{height} = {width * height / 1_000_000:.1f}MP). "
                            f"This server's limit is {limit_mp:g} megapixels."
                        )
                        results.append(file_result)
                        continue
                cover_file.seek(0)
            except UnidentifiedImageError:
                file_result["error"] = "Invalid or corrupt image file."
                results.append(file_result)
                continue

            _, ext = os.path.splitext(original_filename)
            fd, cover_path = tempfile.mkstemp(suffix=ext, dir=_temp_dir())
            os.close(fd)
            cover_file.save(cover_path)

            base_name, _ = os.path.splitext(original_filename)
            output_filename = f"{base_name}_stego.png"
            output_path = os.path.join(batch_output_dir, output_filename)

            try:
                steg_result = stegfile.hide_message(cover_path, output_path, message, key, **steg_options)

                if "psnr" in steg_result:
                    key_filename = f"{base_name}_stego.key"
                    key_save_path = os.path.join(batch_output_dir, key_filename)
                    with open(key_save_path, "w") as kf:
                        kf.write(key)

                    steg_result["file_size"] = os.path.getsize(cover_path) / 1024

                    file_result.update(
                        {"success": True, "outputPath": output_filename, **steg_result}
                    )
                else:
                    file_result["error"] = steg_result.get("message", "Unknown error during processing")
                    current_app.logger.error(f"Batch hide failed for {original_filename}: {file_result['error']}")
            except Exception as e:
                current_app.logger.error(
                    f"Exception during batch hide for {original_filename}: {e}\n{traceback.format_exc()}"
                )
                file_result["error"] = f"A server exception occurred: {e}"
            finally:
                results.append(file_result)
                os.remove(cover_path)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in os.listdir(batch_output_dir):
                zf.write(os.path.join(batch_output_dir, file), arcname=file)
        zip_buffer.seek(0)

        zip_base64 = base64.b64encode(zip_buffer.read()).decode("utf-8")
        zip_filename = f"stego_batch_results_{datetime.now().strftime('%Y%m%d')}.zip"

        return jsonify(
            {
                "success": True,
                "results": results,
                "zipFile": f"data:application/zip;base64,{zip_base64}",
                "zipFilename": zip_filename,
            }
        )
    except Exception as e:
        current_app.logger.error(f"Critical error in batch_hide endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e), "results": results}), 500
    finally:
        if os.path.exists(batch_output_dir):
            shutil.rmtree(batch_output_dir)


@api_bp.route("/batch_extract", methods=["POST"])
def batch_extract():
    results, temp_files_to_clean, consolidated_text_output = [], [], []
    try:
        data = request.form
        key = data.get("key") or None
        stego_files = request.files.getlist("stegoImages")
        if not stego_files:
            return jsonify({"success": False, "error": "No stego images provided"}), 400

        param_map = {
            "useAES": "use_aes",
            "enhancedBit": "enhanced_bit",
            "adaptiveChannel": "adaptive_channel",
            "extractKey": "extract_key",
        }
        steg_options = {param_map[k]: (v == "true") for k, v in data.items() if k in param_map}
        steg_options["return_raw"] = True

        for stego_file in stego_files:
            original_filename = secure_filename(stego_file.filename)
            file_result = {"filename": original_filename, "success": False}
            stego_path = None
            try:
                _, ext = os.path.splitext(original_filename)
                fd, stego_path = tempfile.mkstemp(suffix=ext, dir=_temp_dir())
                os.close(fd)
                stego_file.save(stego_path)
                temp_files_to_clean.append(stego_path)

                requested_enhanced = steg_options.get("enhanced_bit", False)
                requested_adaptive = steg_options.get("adaptive_channel", False)

                extract_result = stegfile.extract_message(stego_path, key, **steg_options)

                is_error = "message" in extract_result and extract_result["message"].startswith("ERROR:")

                mode_mismatch_detected = False
                if is_error:
                    # See the single-extract endpoint for why this retry is safe -
                    # a real mismatch resolves cleanly, a genuine failure (wrong
                    # key/corrupt image) fails the same way either time.
                    fallback_enhanced = not (requested_enhanced and requested_adaptive)
                    fallback_options = dict(steg_options)
                    fallback_options["enhanced_bit"] = fallback_enhanced
                    fallback_options["adaptive_channel"] = fallback_enhanced
                    fallback_result = stegfile.extract_message(stego_path, key, **fallback_options)
                    if not fallback_result.get("message", "").startswith("ERROR:"):
                        extract_result = fallback_result
                        is_error = False
                        mode_mismatch_detected = True

                if not is_error:
                    file_result.update(
                        {
                            "success": True,
                            "message": extract_result.get("message", ""),
                            "extractedKey": extract_result.get("extracted_key", ""),
                            "rawData": extract_result.get("raw_data", ""),
                            "rawKeyData": extract_result.get("raw_key_data", ""),
                        }
                    )
                    if mode_mismatch_detected:
                        file_result["modeMismatchDetected"] = True

                    unpacked = unpack_file_payload(extract_result.get("message", ""))
                    if unpacked is not None:
                        file_b64 = base64.b64encode(unpacked["data"]).decode("utf-8")
                        mimetype = _guess_mimetype(unpacked["filename"])
                        file_result.update(
                            {
                                "isFile": True,
                                "extractedFilename": unpacked["filename"],
                                "fileSize": len(unpacked["data"]),
                                "fileData": f"data:{mimetype};base64,{file_b64}",
                                "message": f"[File: {unpacked['filename']}, {len(unpacked['data'])} bytes]",
                            }
                        )

                    consolidated_text_output.append(
                        f"--- SUCCESS: {original_filename} ---\nMessage: {file_result['message']}\n\n"
                    )
                else:
                    file_result["error"] = extract_result.get("message")
                    consolidated_text_output.append(f"--- ERROR: {original_filename} ---\n{file_result['error']}\n\n")
            except Exception as e:
                current_app.logger.error(
                    f"Exception during batch extract for {original_filename}: {e}\n{traceback.format_exc()}"
                )
                file_result["error"] = f"A server exception occurred: {e}"
            finally:
                results.append(file_result)

        results_filename = f"batch_extraction_log_{datetime.now().strftime('%Y%m%d')}.txt"

        return jsonify(
            {
                "success": True,
                "results": results,
                "resultsText": "".join(consolidated_text_output),
                "resultsFilename": results_filename,
            }
        )
    except Exception as e:
        current_app.logger.error(f"Critical error in batch_extract endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e), "results": results}), 500
    finally:
        for f in temp_files_to_clean:
            if os.path.exists(f):
                os.remove(f)


@api_bp.route("/batch_performance_graphs", methods=["POST"])
def generate_batch_graphs():
    try:
        batch_results = request.json.get("results", [])
        if not batch_results:
            return jsonify({"success": False, "error": "No results provided for graphing"})

        graphs_dir = os.path.join(current_app.static_folder, "graphs")
        os.makedirs(graphs_dir, exist_ok=True)

        result = visualization.generate_all_graphs(batch_results, graphs_dir)

        if result["success"]:
            graph_urls = [f"/static/graphs/{graph}?v={datetime.now().timestamp()}" for graph in result["graphs"]]
            return jsonify({"success": True, "graphs": graph_urls})
        else:
            return jsonify({"success": False, "error": result.get("error", "Graph generation failed")})
    except Exception as e:
        current_app.logger.error(f"Error in generate_batch_graphs: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)})


@api_bp.route("/graphs/<path:filename>")
def serve_graph(filename):
    # Kept as an explicit route (rather than relying solely on Flask's
    # built-in /static handler) so cache-busting query params behave
    # predictably for graphs generated after app startup.
    return send_from_directory(os.path.join(current_app.static_folder, "graphs"), filename)
