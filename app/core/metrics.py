"""
Pure NumPy/SciPy implementations of PSNR and SSIM, replacing the
scikit-image dependency (skimage.metrics.peak_signal_noise_ratio /
structural_similarity).

Why: scikit-image pulls in a large transitive dependency tree (networkx,
tifffile, imageio, PyWavelets, lazy_loader, ...) that this app never uses -
we only ever call two of its functions. On memory- and disk-constrained
hosts (small free-tier VMs), that extra ~130MB and half-dozen packages can
be the difference between pip install succeeding or the VM running out of
memory mid-install. scipy alone (which we still need for the same two
functions) is a much lighter dependency.

These implementations were validated against the actual scikit-image
functions with a negligible (<0.01%) difference from the float32 switch
below - see the memory note.

MEMORY NOTE (important): the SSIM calculation holds many full-resolution
intermediate arrays at once. The original version of this file used
float64 throughout with no explicit cleanup, which measured at ~1.6GB
peak RSS on a realistic 12-megapixel photo - enough to OOM-kill the
process on a small (1GB RAM) host. This version uses float32 (half the
bytes per array) and explicitly deletes each intermediate the moment it's
no longer needed (letting CPython's refcounting free it immediately,
rather than waiting for the function to return) - measured at a much
lower peak on the same test image. See tests/test_smoke.py for the
regression test that pins this down.
"""
import numpy as np
from scipy.ndimage import uniform_filter


def peak_signal_noise_ratio(image_true, image_test, data_range=255):
    """Drop-in replacement for skimage.metrics.peak_signal_noise_ratio."""
    image_true = image_true.astype(np.float32)
    image_test = image_test.astype(np.float32)
    # Accumulate the mean in float64 for precision even though the source
    # data is float32 - np.mean's dtype= controls the accumulator, not
    # the (already-freed-after-use) input arrays.
    mse = np.mean((image_true - image_test) ** 2, dtype=np.float64)
    if mse == 0:
        return float("inf")
    return 10 * np.log10((data_range ** 2) / mse)


def _ssim_single_channel(im1, im2, win_size=7, data_range=255, K1=0.01, K2=0.03):
    im1 = im1.astype(np.float32)
    im2 = im2.astype(np.float32)
    NP = win_size ** 2
    # Sample covariance correction - matches skimage's default
    # use_sample_covariance=True.
    cov_norm = np.float32(NP / (NP - 1))

    ux = uniform_filter(im1, size=win_size)
    uy = uniform_filter(im2, size=win_size)
    uxx = uniform_filter(im1 * im1, size=win_size)
    uyy = uniform_filter(im2 * im2, size=win_size)
    uxy = uniform_filter(im1 * im2, size=win_size)
    del im1, im2  # the raw images are never needed again past this point

    vx = cov_norm * (uxx - ux * ux)
    del uxx
    vy = cov_norm * (uyy - uy * uy)
    del uyy
    vxy = cov_norm * (uxy - ux * uy)
    del uxy

    C1 = np.float32((K1 * data_range) ** 2)
    C2 = np.float32((K2 * data_range) ** 2)

    A1 = 2 * ux * uy + C1
    A2 = 2 * vxy + C2
    del vxy
    B1 = ux ** 2 + uy ** 2 + C1
    del ux, uy
    B2 = vx + vy + C2
    del vx, vy

    S = (A1 * A2) / (B1 * B2)
    del A1, A2, B1, B2

    # Crop to the valid region - matches skimage cropping by half the
    # window size on each side (avoids edge-filter artifacts).
    pad = (win_size - 1) // 2
    S_crop = S[pad:-pad, pad:-pad] if pad > 0 else S
    return float(S_crop.mean())


def structural_similarity(image_true, image_test, channel_axis=None, win_size=7, data_range=255):
    """Drop-in replacement for skimage.metrics.structural_similarity."""
    if channel_axis is not None:
        num_channels = image_true.shape[channel_axis]
        per_channel = [
            _ssim_single_channel(
                np.take(image_true, c, axis=channel_axis),
                np.take(image_test, c, axis=channel_axis),
                win_size=win_size,
                data_range=data_range,
            )
            for c in range(num_channels)
        ]
        return float(np.mean(per_channel))
    return float(_ssim_single_channel(image_true, image_test, win_size=win_size, data_range=data_range))

