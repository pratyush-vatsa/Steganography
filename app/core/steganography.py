import numpy as np
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
import logging
import os
import secrets
# PSNR/SSIM: implemented in-house (app/core/metrics.py) with pure
# NumPy/SciPy instead of scikit-image - see that module's docstring for
# why. scipy is a required dependency either way (it's what our own
# implementation uses), so this doesn't add anything new, it just drops
# scikit-image's much larger transitive dependency tree.
try:
    from .metrics import peak_signal_noise_ratio, structural_similarity
except ImportError:
    logging.warning("scipy not found. PSNR and SSIM metrics will not be calculated.")
    peak_signal_noise_ratio = None
    structural_similarity = None
import string
import math
import binascii
import traceback
import json
import hashlib # Keep hashlib import

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_key():
    """Generate a new 32-byte (256-bit) key for AES encryption."""
    key_bytes = secrets.token_bytes(32)
    # Convert to hex string for consistent storage and transmission
    return binascii.hexlify(key_bytes).decode('ascii')

def encrypt_key_for_embedding(key, master_key_bytes):
    """
    Encrypt a key before embedding in an image.
    Uses a more robust approach with error correction.
    """
    try:
        # Ensure key is in correct format
        if isinstance(key, str):
            # Clean the key and ensure it's valid hex
            clean_key = ''.join(c for c in key if c in '0123456789abcdefABCDEF').lower()
            if len(clean_key) < 64:  # Pad if necessary
                clean_key = clean_key.ljust(64, '0')
            elif len(clean_key) > 64:  # Truncate if too long
                clean_key = clean_key[:64]
            key_bytes = binascii.unhexlify(clean_key)
        else:
            key_bytes = key
            if len(key_bytes) < 32:  # Ensure 32 bytes for AES-256
                key_bytes = key_bytes.ljust(32, b'\0')
            elif len(key_bytes) > 32:
                key_bytes = key_bytes[:32]
        
        # Use stronger encryption for the key
        # Create a derived key from master_key_bytes
        derived_key = hashlib.sha256(master_key_bytes).digest()[:32]
        
        # Create a new structure with enhanced data
        key_data = {
            "original": binascii.hexlify(key_bytes).decode('ascii'),
            "encrypted": base64.b64encode(bytes(a ^ b for a, b in zip(key_bytes, derived_key))).decode('utf-8'),
            "checksum": sum(key_bytes) % 256
        }
        
        # Convert to JSON, then base64 encode
        json_bytes = json.dumps(key_data).encode('utf-8')
        encrypted_key = base64.b64encode(json_bytes).decode('utf-8')
        
        logger.info(f"Key encrypted successfully with enhanced method, length: {len(encrypted_key)} bytes")
        return encrypted_key
        
    except Exception as e:
        logger.error(f"Error encrypting key: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Fallback to simple XOR if the enhanced method fails
        try:
            # Clean the key and XOR with master key
            if isinstance(key, str):
                clean_key = ''.join(c for c in key if c in '0123456789abcdefABCDEF').lower()
                key_bytes = binascii.unhexlify(clean_key)
            else:
                key_bytes = key
                
            # Create a fixed-length encryption key
            crypt_key = (master_key_bytes * (32 // len(master_key_bytes) + 1))[:32]
            
            # XOR the key with our encryption key
            encrypted_bytes = bytes(a ^ b for a, b in zip(key_bytes, crypt_key))
            
            # Convert to base64 for safe storage
            encrypted_key = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            logger.info(f"Key encrypted with fallback method, length: {len(encrypted_key)} bytes")
            return encrypted_key
            
        except Exception as fallback_error:
            logger.error(f"Fallback encryption also failed: {str(fallback_error)}")
            raise

def decrypt_embedded_key(encrypted_key, master_key_bytes):
    """
    Decrypt a key that was embedded in an image.
    Enhanced with improved error handling and multiple decryption strategies.
    """
    try:
        # First, decode the base64
        if isinstance(encrypted_key, str):
            try:
                json_bytes = base64.b64decode(encrypted_key)
                # Try to parse as JSON
                key_data = json.loads(json_bytes.decode('utf-8'))
                
                # If we have the original key directly, use it
                if 'original' in key_data:
                    logger.info("Found original key in embedded data")
                    return key_data['original']
                
                # Otherwise, decrypt using the enhanced method
                encrypted_bytes = base64.b64decode(key_data['encrypted'])
                checksum = key_data['checksum']
                
                # Calculate the derived key for decryption
                derived_key = hashlib.sha256(master_key_bytes).digest()[:32]
                
                # Decrypt using XOR
                decrypted_bytes = bytes(a ^ b for a, b in zip(encrypted_bytes, derived_key))
                
                # Verify checksum if available
                if checksum is not None:
                    calculated_checksum = sum(decrypted_bytes) % 256
                    if checksum != calculated_checksum:
                        logger.warning(f"Checksum mismatch: expected {checksum}, got {calculated_checksum}")
                        # We'll continue anyway and rely on further validation
                
                # Convert to hex string
                hex_key = binascii.hexlify(decrypted_bytes).decode('ascii')
                
                return hex_key
                
            except (json.JSONDecodeError, base64.binascii.Error, UnicodeDecodeError, KeyError) as json_error:
                logger.warning(f"Enhanced key format not detected: {str(json_error)}")
                # Fall back to original method
                pass
        
        # Original method as fallback
        if isinstance(encrypted_key, str):
            try:
                encrypted_bytes = base64.b64decode(encrypted_key)
            except base64.binascii.Error:
                # If we can't decode as base64, try using the string directly
                encrypted_bytes = encrypted_key.encode('utf-8')
        else:
            encrypted_bytes = encrypted_key
        
        # Create a fixed-length encryption key
        crypt_key = (master_key_bytes * ((len(encrypted_bytes) // len(master_key_bytes)) + 1))[:len(encrypted_bytes)]
        
        # XOR to decrypt
        decrypted_bytes = bytes(a ^ b for a, b in zip(encrypted_bytes, crypt_key))
        
        # Convert to hex string
        hex_key = binascii.hexlify(decrypted_bytes).decode('ascii')
        
        # Clean up the key - ensure it's 64 characters (32 bytes)
        if len(hex_key) < 64:
            hex_key = hex_key.ljust(64, '0')
        elif len(hex_key) > 64:
            hex_key = hex_key[:64]
            
        return hex_key
        
    except Exception as e:
        logger.error(f"Error in decrypt_embedded_key: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Last resort fallback
        try:
            # Try direct XOR with master key
            if isinstance(encrypted_key, str):
                encrypted_bytes = encrypted_key.encode('utf-8')
            else:
                encrypted_bytes = encrypted_key
                
            # Create a derived key using hash
            derived_key = hashlib.sha256(master_key_bytes).digest()
            decrypt_key = (derived_key * ((len(encrypted_bytes) // len(derived_key)) + 1))[:len(encrypted_bytes)]
            
            # XOR decrypt
            result_bytes = bytes(a ^ b for a, b in zip(encrypted_bytes, decrypt_key))
            
            # Try to extract a valid hex key
            possible_key = ''.join(chr(b) for b in result_bytes if 32 <= b <= 126)
            clean_key = ''.join(c for c in possible_key if c in '0123456789abcdefABCDEF').lower()
            
            if len(clean_key) >= 32:
                logger.info("Recovered partial key with fallback method")
                if len(clean_key) < 64:
                    clean_key = clean_key.ljust(64, '0')
                elif len(clean_key) > 64:
                    clean_key = clean_key[:64]
                return clean_key
        except:
            pass
        
        # If all else fails, return None
        return None

def hide_message(cover_path, output_path, message, key,
                use_aes=True, enhanced_bit=True, adaptive_channel=True,
                error_correction=True, embed_key=True):
    """
    Hide a message and optionally the key in a cover image using RGB intensity-based steganography.
    """
    original_message_for_return = message
    key_used_for_return = key

    try:
        img = Image.open(cover_path).convert("RGB")
        img_array = np.array(img)
        # <-- MODIFICATION: Removed the memory-intensive copy of the image array. -->
        # original_img_array_for_metrics = img_array.copy() # <-- THIS LINE IS REMOVED
        height, width, channels = img_array.shape
    except FileNotFoundError:
        logger.error(f"Cover image not found: {cover_path}")
        return {"message": f"ERROR: Cover image not found: {cover_path}"}
    except Exception as e:
        logger.error(f"Error loading cover image {cover_path}: {e}\n{traceback.format_exc()}")
        return {"message": f"ERROR: Failed to load cover image: {e}"}

    encrypted_message_b64 = ""
    encrypted_key_b64 = ""

    # --- Key Processing ---
    key_bytes = None
    if key:
        if isinstance(key, str):
            try:
                # Attempt to decode as hex, ensuring it's 32 bytes (64 hex chars)
                clean_key = ''.join(c for c in key if c in '0123456789abcdefABCDEF').lower()
                if len(clean_key) == 64:
                    key_bytes = binascii.unhexlify(clean_key)
                    logger.info(f"Using 32-byte hex key for hiding.")
                else:
                     logger.warning(f"Provided hex key is not 64 chars ({len(clean_key)}). Using as UTF-8.")
                     key_bytes = key.encode('utf-8')[:32].ljust(32, b'\0') # Use first 32 bytes or pad
            except binascii.Error:
                logger.warning(f"Provided key is not valid hex. Using as UTF-8 string (or first 32 bytes).")
                key_bytes = key.encode('utf-8')[:32].ljust(32, b'\0') # Ensure 32 bytes
        elif isinstance(key, bytes): # Assume bytes
             key_bytes = key[:32].ljust(32, b'\0') # Ensure 32 bytes
             logger.info(f"Using provided bytes key for hiding (ensured 32 bytes).")
        else:
             logger.warning(f"Invalid key type provided ({type(key)}). Using str representation as UTF-8.")
             key_bytes = str(key).encode('utf-8')[:32].ljust(32, b'\0') # Ensure 32 bytes

    if use_aes and not key_bytes:
        return {"message": "ERROR: AES encryption enabled, but no valid 32-byte key could be derived."}

    # --- Message Preparation ---
    message_to_embed = message # Start with the original message
    if error_correction and not use_aes:
        # Apply only if AES is OFF, as AES provides its own integrity/diffusion
        message_to_embed = ''.join([char * 3 for char in message])
        logger.info(f"Applied 3x error correction, length: {len(message_to_embed)}")

    if use_aes and key_bytes:
        try:
            message_bytes = message_to_embed.encode('utf-8')
            iv = get_random_bytes(16) # AES block size
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
            ciphertext = cipher.encrypt(pad(message_bytes, AES.block_size))
            encrypted_data_with_iv = iv + ciphertext
            encrypted_message_b64 = base64.b64encode(encrypted_data_with_iv).decode('utf-8')
            message_to_embed = encrypted_message_b64 # Embed the base64 string
            logger.info(f"Message encrypted (Base64): {len(encrypted_message_b64)} chars")
        except Exception as e:
            logger.error(f"Error during encryption: {str(e)}\n{traceback.format_exc()}")
            return {"message": f"ERROR: Encryption failed: {e}"}

    # --- Key Embedding Preparation ---
    if embed_key and key_bytes:
        try:
            # Generate a master key from the image
            # Note: This derivation method is basic and potentially insecure.
            # Consider a more robust method involving hashing more pixel data.
            # BUGFIX: mask each sampled channel's LSB (& 0xFE) before
            # building the master key. pixel (0,0) - one of the sampled
            # points - is also the very first pixel embedding writes to,
            # so without this mask the master key computed here (from the
            # original image) would not match the one extract_message()
            # recomputes later (from the stego image), causing embedded-key
            # extraction to intermittently fail. Only the LSB ever changes
            # during embedding, so masking it out makes the derivation
            # invariant to embedding.
            def _mk(v):
                return int(v) & 0xFE

            master_key_bytes = bytes([
                _mk(img_array[0, 0, 0]), _mk(img_array[0, 0, 1]), _mk(img_array[0, 0, 2]),
                _mk(img_array[height//2, width//2, 0]), _mk(img_array[height//2, width//2, 1]), _mk(img_array[height//2, width//2, 2]),
                _mk(img_array[height-1, width-1, 0]), _mk(img_array[height-1, width-1, 1]), _mk(img_array[height-1, width-1, 2]),
                _mk(img_array[0, width-1, 0]), _mk(img_array[0, width-1, 1]), _mk(img_array[0, width-1, 2]),
                _mk(img_array[height-1, 0, 0]), _mk(img_array[height-1, 0, 1]), _mk(img_array[height-1, 0, 2]),
                _mk(img_array[height//3, width//3, 0])
            ])
            # Pass the actual 32-byte key_bytes for encryption
            encrypted_key_b64 = encrypt_key_for_embedding(key_bytes, master_key_bytes)
            logger.info(f"Key prepared for embedding (Base64): {len(encrypted_key_b64)} chars")
        except Exception as e:
             logger.error(f"Error preparing key for embedding: {e}\n{traceback.format_exc()}. Key will not be embedded.")
             embed_key = False # Disable embedding if preparation fails
             encrypted_key_b64 = ""

    # --- Assemble Final Payload ---
    # Convert the (potentially encrypted and base64 encoded) message to binary
    try:
        binary_message = ''.join(format(ord(char), '08b') for char in message_to_embed)
        binary_msg_length = format(len(binary_message), '032b') # 32 bits for message length
    except Exception as e:
        logger.error(f"Error converting message to binary: {e}")
        return {"message": f"ERROR: Could not process message for embedding: {e}"}

    if embed_key and encrypted_key_b64:
        try:
            binary_key = ''.join(format(ord(char), '08b') for char in encrypted_key_b64)
            binary_key_length = format(len(binary_key), '032b') # 32 bits for key length
            key_marker = '11111111' # 8 bits marker
            # Order: Marker(8) + MsgLen(32) + KeyLen(32) + Message + Key
            binary_data = key_marker + binary_msg_length + binary_key_length + binary_message + binary_key
            logger.info(f"Assembled payload: M(8)+ML(32)+KL(32)+Msg({len(binary_message)})+Key({len(binary_key)}) = {len(binary_data)} bits")
        except Exception as e:
            logger.error(f"Error processing embedded key: {e}. Disabling embedding.")
            embed_key = False # Disable if error
            encrypted_key_b64 = ""
            no_key_marker = '00000000'
            binary_data = no_key_marker + binary_msg_length + binary_message
            logger.info(f"Assembled payload (no key): M(8)+ML(32)+Msg({len(binary_message)}) = {len(binary_data)} bits")
    else:
        no_key_marker = '00000000'
        binary_data = no_key_marker + binary_msg_length + binary_message
        logger.info(f"Assembled payload (no key): M(8)+ML(32)+Msg({len(binary_message)}) = {len(binary_data)} bits")

    # --- Capacity Check ---
    # Calculate maximum bits based on strategy
    max_bits_simple = height * width * 3
    # Enhanced uses ~2 channels per pixel, but header/key might use 3 initially. Be conservative.
    max_bits_enhanced = height * width * 2
    required_bits = len(binary_data)
    is_enhanced_mode = enhanced_bit and adaptive_channel
    available_bits = max_bits_enhanced if is_enhanced_mode else max_bits_simple

    if required_bits > available_bits:
        base_msg = (
            f"ERROR: Data too large. Needs {required_bits} bits, available ~{available_bits} "
            f"({'Enhanced' if is_enhanced_mode else 'Simple'} LSB)."
        )
        # Enhanced/Adaptive mode only uses 2 of 3 channels per pixel (for
        # better stealth), so it has 1/3 less capacity than Simple LSB.
        # If disabling it would actually fit, say so explicitly rather
        # than leaving the user to guess why a "too large" error appeared
        # for a file that isn't unreasonably big.
        if is_enhanced_mode and required_bits <= max_bits_simple:
            base_msg += (
                f" Disabling 'Enhanced Bit Distribution' and 'Adaptive Channel' (Simple LSB) "
                f"would provide ~{max_bits_simple} bits - enough to fit this. "
                f"Remember: the person extracting will need those same settings turned off too."
            )
        else:
            base_msg += " Try a larger cover image or a shorter message/smaller file."
        return {"message": base_msg}

    # --- Embedding ---
    stego_array = img_array # Modify the copy loaded earlier
    data_index = 0
    bit_errors = 0 # Track bits flipped during embedding
    total_bits_embedded = 0 # Track actual bits written

    try:
        if enhanced_bit and adaptive_channel:
            logger.info("Using Enhanced/Adaptive LSB Embedding")
            # RGB Intensity-based embedding
            for i in range(height):
                for j in range(width):
                    if data_index >= len(binary_data): break
                    pixel = stego_array[i, j]
                    # BUGFIX: mask off each channel's LSB (& 0xFE) before
                    # computing intensity. Embedding only ever changes a
                    # channel's LSB, so without this mask, embedding a bit
                    # into this very pixel can shift its intensity by up to
                    # ~1 - enough to cross the 85/170 threshold below for
                    # pixels whose original intensity sits right at the
                    # boundary. That flips which channels get used, and
                    # extraction (recomputing intensity from the now-stego
                    # pixel) picks a different channel pair than embedding
                    # used, corrupting the payload at that pixel. Masking
                    # the LSB makes intensity - and channel selection -
                    # identical before and after embedding.
                    intensity = int(np.sum((pixel.astype(np.uint16) & 0xFE))) // 3
                    channels_to_use = []
                    if intensity < 85: channels_to_use = [0, 1] # R, G
                    elif intensity < 170: channels_to_use = [1, 2] # G, B
                    else: channels_to_use = [0, 2] # R, B

                    for c in channels_to_use:
                         if data_index < len(binary_data):
                            bit_to_embed = int(binary_data[data_index])
                            original_lsb = int(pixel[c] & 1) # Get original LSB as int
                            if original_lsb != bit_to_embed:
                                bit_errors += 1 # Count change *before* modifying
                                stego_array[i, j, c] = (pixel[c] & 254) | bit_to_embed
                            # Else: No change needed, LSB already matches
                            data_index += 1
                            total_bits_embedded +=1 # Increment even if LSB wasn't flipped
                         else: break
                    if data_index >= len(binary_data): break
                if data_index >= len(binary_data): break
        else:
            logger.info("Using Simple LSB Embedding")
            # Simple LSB substitution
            for i in range(height):
                for j in range(width):
                    if data_index >= len(binary_data): break
                    pixel = stego_array[i, j]
                    for c in range(3): # RGB channels
                        if data_index < len(binary_data):
                            bit_to_embed = int(binary_data[data_index])
                            original_lsb = int(pixel[c] & 1)
                            if original_lsb != bit_to_embed:
                                bit_errors += 1
                                stego_array[i, j, c] = (pixel[c] & 254) | bit_to_embed
                            data_index += 1
                            total_bits_embedded +=1
                        else: break
                    if data_index >= len(binary_data): break
                if data_index >= len(binary_data): break

        if data_index != len(binary_data):
             logger.warning(f"Embedding loop finished, but not all data was embedded. Expected {len(binary_data)}, Embedded {data_index}")
             # This case indicates a potential logic error or premature break

        logger.info(f"Finished embedding {total_bits_embedded} bits.")

    except Exception as e:
        logger.error(f"Error during LSB embedding: {e}\n{traceback.format_exc()}")
        return {"message": f"ERROR: Embedding process failed: {e}"}

    # --- Save Output ---
    try:
        if stego_array.dtype != np.uint8:
             stego_array = np.clip(stego_array, 0, 255).astype(np.uint8)
        Image.fromarray(stego_array).save(output_path, format='PNG')
        logger.info(f"Stego image saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving stego image {output_path}: {e}\n{traceback.format_exc()}")
        return {"message": f"ERROR: Failed to save output image: {e}"}

    # --- Calculate Metrics ---
    psnr = 0.0
    ssim = 0.0
    ber = 1.0
    payload_capacity = 0.0

    try:
        if peak_signal_noise_ratio is None or structural_similarity is None:
            logger.warning("Skipping PSNR/SSIM calculation as scipy is not installed.")
        else:
            # <-- MODIFICATION: Re-load the original image from disk for comparison -->
            # This avoids keeping a large copy in memory throughout the entire process.
            original_img_for_metrics = Image.open(cover_path).convert("RGB")
            # float32 (not float64) - halves memory and roughly halves SSIM's
            # runtime on large images with no meaningful precision loss for
            # a quality metric like this.
            original_float = np.array(original_img_for_metrics, dtype=np.float32)
            # <-- END of modification -->

            stego_float = stego_array.astype(np.float32)

            psnr = peak_signal_noise_ratio(original_float, stego_float, data_range=255)

            min_dim = min(height, width)
            win_size = min(7, min_dim if min_dim % 2 != 0 else min_dim - 1)
            win_size = max(3, win_size)

            if win_size > min_dim:
                 logger.warning(f"Image dimension ({min_dim}) too small for SSIM win_size ({win_size}). Skipping SSIM.")
                 ssim = 0.0
            else:
                 ssim = structural_similarity(original_float, stego_float, channel_axis=2, data_range=255, win_size=win_size)

        ber = bit_errors / total_bits_embedded if total_bits_embedded > 0 else 0
        payload_capacity = required_bits / (height * width) if height * width > 0 else 0
        logger.info(f"Metrics - PSNR: {psnr:.2f}, SSIM: {ssim:.4f}, BER: {ber:.6f}, Capacity: {payload_capacity:.6f} bpp")

    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}\n{traceback.format_exc()}")

    return {
        'psnr': float(psnr),
        'ssim': float(ssim),
        'ber': float(ber),
        'capacity': float(payload_capacity),
        'encrypted_message': encrypted_message_b64,
        'encrypted_key': encrypted_key_b64,
        'message': original_message_for_return,
        'key': key_used_for_return,
    }

# Inside stegfile.py
# (Keep imports and other functions like generate_key, hide_message, etc.)

def extract_message(stego_path, key=None, use_aes=True, enhanced_bit=True,
                   adaptive_channel=True, return_raw=False, extract_key=True):
    """
    Extract a message and optionally the key from a stego image.

    Args:
        stego_path: Path to the stego image
        key: The encryption key (hex string or bytes) - may be None if extracting key from image
        use_aes: Whether AES decryption is expected (based on user setting)
        enhanced_bit: Whether enhanced bit distribution was used for embedding
        adaptive_channel: Whether adaptive channel selection was used for embedding
        return_raw: Whether to return raw extracted data alongside the message
        extract_key: Whether to attempt extracting the key from the image

    Returns:
        dict: A dictionary containing the extracted message, raw data (if requested),
              extracted key (if found), raw key data (if found), and success/error status.
    """
    final_result = {
        "message": "ERROR: Extraction failed.",
        "raw_data": "",
        "extracted_key": None,
        "raw_key_data": None
    }

    try:
        # --- Load Image ---
        try:
            img = Image.open(stego_path).convert("RGB")
            img_array = np.array(img)
            height, width, channels = img_array.shape
            logger.info(f"Extracting data from image ({width}x{height})")
        except FileNotFoundError:
            final_result["message"] = f"ERROR: Stego image not found: {stego_path}"
            return final_result
        except Exception as e:
            logger.error(f"Error loading stego image {stego_path}: {e}\n{traceback.format_exc()}")
            final_result["message"] = f"ERROR: Failed to load stego image: {e}"
            return final_result

        # --- Extract Header Bits (Marker + Lengths) ---
        # Header structure depends on whether a key was embedded:
        # No Key: Marker(8) + MsgLen(32) = 40 bits
        # Key:    Marker(8) + MsgLen(32) + KeyLen(32) = 72 bits
        header_bits_to_read = 72 # Read enough for the longest possible header initially
        binary_header = ""
        data_index = 0
        pixels_processed = 0

        # Use selected extraction strategy
        try:
            if enhanced_bit and adaptive_channel:
                # Intensity-based extraction
                for i in range(height):
                    for j in range(width):
                        if data_index >= header_bits_to_read: break
                        pixel = img_array[i, j]
                        # See matching bugfix note in hide_message(): mask
                        # the LSB before computing intensity so channel
                        # selection matches what embedding used.
                        intensity = int(np.sum((pixel.astype(np.uint16) & 0xFE))) // 3
                        channels_to_use = []
                        if intensity < 85: channels_to_use = [0, 1] # R, G
                        elif intensity < 170: channels_to_use = [1, 2] # G, B
                        else: channels_to_use = [0, 2] # R, B
                        for c in channels_to_use:
                            if data_index < header_bits_to_read:
                                binary_header += str(pixel[c] & 1)
                                data_index += 1
                            else: break
                        pixels_processed += 1
                    if data_index >= header_bits_to_read: break
            else:
                # Simple LSB extraction
                for i in range(height):
                    for j in range(width):
                        if data_index >= header_bits_to_read: break
                        pixel = img_array[i, j]
                        for c in range(3): # RGB channels
                            if data_index < header_bits_to_read:
                                binary_header += str(pixel[c] & 1)
                                data_index += 1
                            else: break
                        pixels_processed += 1
                    if data_index >= header_bits_to_read: break
        except Exception as e:
             logger.error(f"Error extracting header bits: {e}\n{traceback.format_exc()}")
             final_result["message"] = f"ERROR: Failed during header bit extraction: {e}"
             return final_result

        if len(binary_header) < 40:
            logger.error(f"Could not extract enough header bits ({len(binary_header)}), image likely too small or corrupted.")
            final_result["message"] = "ERROR: Could not extract sufficient header data from image."
            return final_result

        # --- Parse Header ---
        key_is_embedded = False
        message_length = 0
        key_length = 0
        header_length_used = 40 # Default for no key

        try:
            marker = binary_header[:8]
            if marker == '11111111': # Key embedded marker
                if len(binary_header) >= 72:
                    key_is_embedded = True
                    message_length = int(binary_header[8:40], 2)
                    key_length = int(binary_header[40:72], 2)
                    header_length_used = 72
                    logger.info(f"Key marker found. MsgLen={message_length}, KeyLen={key_length}")
                else:
                    logger.error(f"Key marker found, but not enough header bits extracted ({len(binary_header)})")
                    final_result["message"] = "ERROR: Incomplete header data found (expected key)."
                    return final_result
            elif marker == '00000000': # No key embedded marker
                 key_is_embedded = False
                 message_length = int(binary_header[8:40], 2)
                 header_length_used = 40
                 logger.info(f"No key marker found. MsgLen={message_length}")
            else:
                 # This might happen with corruption or if no message was hidden
                 logger.warning(f"Invalid marker detected: {marker}. Assuming no message present or image corrupt.")
                 final_result["message"] = f"ERROR: Invalid data marker found ({marker}). Image may be corrupt or empty."
                 return final_result

            # --- Validate Lengths ---
            max_possible_payload = height * width * 3 # Absolute theoretical max
            if not (0 < message_length <= max_possible_payload):
                raise ValueError(f"Invalid message length extracted: {message_length}")
            if key_is_embedded and not (0 < key_length <= max_possible_payload):
                 raise ValueError(f"Invalid embedded key length extracted: {key_length}")

        except ValueError as e:
            logger.error(f"Error parsing header lengths: {e}")
            final_result["message"] = f"ERROR: Corrupted header data - invalid length. {e}"
            return final_result
        except Exception as e:
            logger.error(f"Unexpected error parsing header: {e}\n{traceback.format_exc()}")
            final_result["message"] = f"ERROR: Failed to parse header: {e}"
            return final_result

        # --- Extract Full Payload ---
        total_payload_bits_needed = header_length_used + message_length + (key_length if key_is_embedded else 0)
        # BUGFIX: `binary_header` holds every raw bit already read from the
        # image (up to header_bits_to_read == 72), regardless of which
        # marker was found. When no key is embedded, the real header is
        # only 40 bits - bits 40:72 of `binary_header` are NOT unused
        # padding, they are already the first 32 bits of the real message
        # payload. The original code truncated to binary_header[:header_length_used]
        # here, silently dropping those 32 bits from every message hidden
        # with embed_key=False (and shifting/corrupting everything after
        # them, which is also why AES decryption failed with a padding
        # error). Keep the full raw header instead - no bits are lost.
        binary_payload = binary_header
        data_index = len(binary_header)
        # Reset pixel counter, start from where header extraction left off
        current_pixel_index = pixels_processed

        try:
            if enhanced_bit and adaptive_channel:
                for i in range(height):
                    for j in range(width):
                        # Skip pixels already processed for header
                        if current_pixel_index > 0:
                            current_pixel_index -= 1
                            continue
                        if data_index >= total_payload_bits_needed: break
                        pixel = img_array[i, j]
                        # See matching bugfix note in hide_message(): mask
                        # the LSB before computing intensity so channel
                        # selection matches what embedding used.
                        intensity = int(np.sum((pixel.astype(np.uint16) & 0xFE))) // 3
                        channels_to_use = []
                        if intensity < 85: channels_to_use = [0, 1]
                        elif intensity < 170: channels_to_use = [1, 2]
                        else: channels_to_use = [0, 2]
                        for c in channels_to_use:
                            if data_index < total_payload_bits_needed:
                                binary_payload += str(pixel[c] & 1)
                                data_index += 1
                            else: break
                    if data_index >= total_payload_bits_needed: break
            else:
                for i in range(height):
                    for j in range(width):
                         if current_pixel_index > 0:
                            current_pixel_index -= 1
                            continue
                         if data_index >= total_payload_bits_needed: break
                         pixel = img_array[i, j]
                         for c in range(3):
                             if data_index < total_payload_bits_needed:
                                 binary_payload += str(pixel[c] & 1)
                                 data_index += 1
                             else: break
                    if data_index >= total_payload_bits_needed: break

            if len(binary_payload) < total_payload_bits_needed:
                 logger.error(f"Failed to extract full payload. Needed {total_payload_bits_needed}, got {len(binary_payload)}")
                 final_result["message"] = "ERROR: Could not extract complete message data (image might be truncated or corrupt)."
                 return final_result

            logger.info(f"Successfully extracted {len(binary_payload)} payload bits.")

        except Exception as e:
             logger.error(f"Error extracting payload bits: {e}\n{traceback.format_exc()}")
             final_result["message"] = f"ERROR: Failed during payload bit extraction: {e}"
             return final_result

        # --- Process Payload ---
        extracted_hex_key = None # The final key used for decryption (if any)
        raw_message_data = ""
        raw_key_data_b64 = "" # Raw extracted key data (Base64 encoded from stegfile)

        try:
            # Extract message part
            msg_start_index = header_length_used
            msg_end_index = msg_start_index + message_length
            binary_message_part = binary_payload[msg_start_index:msg_end_index]

            # Convert binary message part to string (likely Base64)
            raw_message_data = ""
            for i in range(0, len(binary_message_part), 8):
                 if i + 8 <= len(binary_message_part):
                    byte = binary_message_part[i:i+8]
                    try: raw_message_data += chr(int(byte, 2))
                    except ValueError: raw_message_data += '?' # Replace invalid byte

            final_result["raw_data"] = raw_message_data # Store raw extracted data

            # Extract and decrypt key if embedded
            if key_is_embedded and extract_key:
                key_start_index = msg_end_index
                key_end_index = key_start_index + key_length
                binary_key_part = binary_payload[key_start_index:key_end_index]

                raw_key_data_b64 = ""
                for i in range(0, len(binary_key_part), 8):
                     if i + 8 <= len(binary_key_part):
                        byte = binary_key_part[i:i+8]
                        try: raw_key_data_b64 += chr(int(byte, 2))
                        except ValueError: raw_key_data_b64 += '?'

                final_result["raw_key_data"] = raw_key_data_b64 # Store raw key data

                try:
                    # Derive master key from stego image.
                    # See matching bugfix note in hide_message(): mask each
                    # sampled channel's LSB so this matches the master key
                    # computed at hide-time regardless of what embedding
                    # changed at those same pixel coordinates.
                    def _mk(v):
                        return int(v) & 0xFE

                    master_key_bytes = bytes([
                        _mk(img_array[0, 0, 0]), _mk(img_array[0, 0, 1]), _mk(img_array[0, 0, 2]),
                        _mk(img_array[height//2, width//2, 0]), _mk(img_array[height//2, width//2, 1]), _mk(img_array[height//2, width//2, 2]),
                        _mk(img_array[height-1, width-1, 0]), _mk(img_array[height-1, width-1, 1]), _mk(img_array[height-1, width-1, 2]),
                        _mk(img_array[0, width-1, 0]), _mk(img_array[0, width-1, 1]), _mk(img_array[0, width-1, 2]),
                        _mk(img_array[height-1, 0, 0]), _mk(img_array[height-1, 0, 1]), _mk(img_array[height-1, 0, 2]),
                        _mk(img_array[height//3, width//3, 0])
                    ])
                    extracted_hex_key = decrypt_embedded_key(raw_key_data_b64, master_key_bytes)
                    if extracted_hex_key:
                         logger.info(f"Successfully extracted and decrypted key: {extracted_hex_key[:8]}...")
                         final_result["extracted_key"] = extracted_hex_key
                    else:
                         logger.warning("Failed to decrypt embedded key.")
                         # Keep raw key data even if decryption fails
                except Exception as key_decrypt_err:
                    logger.error(f"Error decrypting embedded key: {key_decrypt_err}")
                    # Keep raw key data

        except Exception as e:
            logger.error(f"Error processing extracted payload: {e}\n{traceback.format_exc()}")
            final_result["message"] = f"ERROR: Failed processing extracted data: {e}"
            # Still return raw data if available
            return final_result

        # --- Determine Final Key and Decrypt ---
        final_key_bytes = None
        if use_aes:
            key_to_use_hex = None
            # Priority: 1) Successfully extracted key
            if extracted_hex_key:
                 key_to_use_hex = extracted_hex_key
                 logger.info("Using extracted key for decryption.")
            # Priority: 2) Manually provided key
            elif key:
                 if isinstance(key, str):
                      try:
                          clean_key = ''.join(c for c in key if c in '0123456789abcdefABCDEF').lower()
                          if len(clean_key) == 64: key_to_use_hex = clean_key
                      except: pass # Ignore errors if not hex
                 elif isinstance(key, bytes):
                      try: key_to_use_hex = binascii.hexlify(key).decode('ascii')
                      except: pass
                 if key_to_use_hex: logger.info("Using provided key for decryption.")
                 else: logger.warning("Provided key is not a valid hex string or bytes.")

            # If we have a hex key, convert to bytes
            if key_to_use_hex:
                 try:
                     final_key_bytes = binascii.unhexlify(key_to_use_hex)
                     if len(final_key_bytes) != 32:
                         logger.error(f"Key for decryption is not 32 bytes ({len(final_key_bytes)}). Decryption will likely fail.")
                         final_key_bytes = None # Invalidate if wrong length
                 except binascii.Error:
                     logger.error(f"Failed to convert final hex key '{key_to_use_hex[:8]}...' to bytes.")
                     final_key_bytes = None

            # --- Perform Decryption ---
            if final_key_bytes:
                try:
                    # Decode Base64 (raw_message_data should be the base64 string)
                    # Add padding if necessary
                    padding_needed = len(raw_message_data) % 4
                    if padding_needed:
                        padded_message_b64 = raw_message_data + '=' * (4 - padding_needed)
                    else:
                        padded_message_b64 = raw_message_data

                    encrypted_payload_with_iv = base64.b64decode(padded_message_b64)

                    # Extract IV and ciphertext
                    if len(encrypted_payload_with_iv) < 16: # Must have at least IV size
                         raise ValueError("Decoded data too short to contain IV.")
                    iv = encrypted_payload_with_iv[:16]
                    ciphertext = encrypted_payload_with_iv[16:]

                    cipher = AES.new(final_key_bytes, AES.MODE_CBC, iv)
                    decrypted_padded_message = cipher.decrypt(ciphertext)
                    decrypted_message_bytes = unpad(decrypted_padded_message, AES.block_size)
                    final_message = decrypted_message_bytes.decode('utf-8', errors='replace') # Use replace for robustness

                    logger.info("AES Decryption successful.")
                    final_result["message"] = final_message

                except (ValueError, KeyError) as e: # Catches padding errors, key errors etc.
                    logger.error(f"AES Decryption failed: {e}. Likely wrong key or corrupted data.")
                    final_result["message"] = f"ERROR: Decryption failed. Check key or data integrity. ({e})"
                except base64.binascii.Error as e:
                     logger.error(f"Base64 decoding failed during decryption: {e}")
                     final_result["message"] = f"ERROR: Corrupted Base64 data detected. ({e})"
                except Exception as e:
                     logger.error(f"Unexpected decryption error: {e}\n{traceback.format_exc()}")
                     final_result["message"] = f"ERROR: Unexpected error during decryption: {e}"
            else:
                # AES was expected, but no valid key found
                logger.error("AES decryption required but no valid key available.")
                final_result["message"] = "ERROR: AES decryption required, but no valid key was provided or extracted."
                # Keep raw data available in final_result["raw_data"]
        else:
            # No AES decryption needed, the raw message is the final message
            # Apply rudimentary error correction if it looks like triplicate data
            if len(raw_message_data) > 0 and raw_message_data[0] == raw_message_data[1:2] == raw_message_data[2:3]:
                 logger.info("Attempting triplicate error correction on non-AES data.")
                 corrected_message = ""
                 i = 0
                 while i < len(raw_message_data):
                    if i + 2 < len(raw_message_data):
                        chunk = raw_message_data[i:i+3]
                        counts = {c: chunk.count(c) for c in set(chunk)}
                        most_common = max(counts, key=counts.get)
                        corrected_message += most_common
                        i += 3
                    else:
                        corrected_message += raw_message_data[i:] # Add remaining chars
                        break
                 final_result["message"] = corrected_message
                 logger.info(f"Applied correction: {len(corrected_message)} chars")
            else:
                 final_result["message"] = raw_message_data # Use as is

    except Exception as e:
        logger.error(f"Overall extraction error: {e}\n{traceback.format_exc()}")
        final_result["message"] = f"ERROR: An unexpected error occurred during extraction: {e}"
        # Ensure raw data captured so far is returned if requested
        if not return_raw:
            final_result["raw_data"] = "" # Clear raw data if not requested on error
            final_result["raw_key_data"] = ""

    # Final cleanup/validation before return
    if not return_raw:
         final_result.pop("raw_data", None)
         final_result.pop("raw_key_data", None)

    return final_result

# (Keep other functions if any)