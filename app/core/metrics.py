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
functions with an exact (0.00) difference across grayscale, color,
identical-image, small-image, and large (1080x1080) realistic test cases -
they compute precisely the same formulas with the same default parameters
(win_size=7, K1=0.01, K2=0.03, sample covariance correction), not an
approximation.
"""
import numpy as np
from scipy.ndimage import uniform_filter


def peak_signal_noise_ratio(image_true, image_test, data_range=255):
    """Drop-in replacement for skimage.metrics.peak_signal_noise_ratio."""
    image_true = image_true.astype(np.float64)
    image_test = image_test.astype(np.float64)
    mse = np.mean((image_true - image_test) ** 2)
    if mse == 0:
        return float("inf")
    return 10 * np.log10((data_range ** 2) / mse)


def _ssim_single_channel(im1, im2, win_size=7, data_range=255, K1=0.01, K2=0.03):
    im1 = im1.astype(np.float64)
    im2 = im2.astype(np.float64)
    NP = win_size ** 2
    # Sample covariance correction - matches skimage's default
    # use_sample_covariance=True.
    cov_norm = NP / (NP - 1)

    ux = uniform_filter(im1, size=win_size)
    uy = uniform_filter(im2, size=win_size)
    uxx = uniform_filter(im1 * im1, size=win_size)
    uyy = uniform_filter(im2 * im2, size=win_size)
    uxy = uniform_filter(im1 * im2, size=win_size)

    vx = cov_norm * (uxx - ux * ux)
    vy = cov_norm * (uyy - uy * uy)
    vxy = cov_norm * (uxy - ux * uy)

    C1 = (K1 * data_range) ** 2
    C2 = (K2 * data_range) ** 2

    A1 = 2 * ux * uy + C1
    A2 = 2 * vxy + C2
    B1 = ux ** 2 + uy ** 2 + C1
    B2 = vx + vy + C2
    S = (A1 * A2) / (B1 * B2)

    # Crop to the valid region - matches skimage cropping by half the
    # window size on each side (avoids edge-filter artifacts).
    pad = (win_size - 1) // 2
    S_crop = S[pad:-pad, pad:-pad] if pad > 0 else S
    return S_crop.mean()


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
