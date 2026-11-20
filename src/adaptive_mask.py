"""Experimental color-neutral paper segmentation for scanned illustrations.

The algorithm ONLY produces alpha. The original CMYK channels and ICC remain
unchanged in the TIFF writers. Work in Lab for color-neutral detection.
"""
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter


def adaptive_alpha(rgb, sigma_papel=100, threshold=6.0, transition=12.0):
    """Estimate alpha from paper vs pigment differences; values in [0, 1].

    Assumes paper is present near image boundaries. Works for different hues
    but cannot distinguish very pale pigment from similar paper with certainty.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError('Expected HxWx3 RGB')
    if not np.isfinite(rgb).all():
        raise ValueError('Non-finite RGB')
    if threshold < 0 or transition <= 0 or sigma_papel <= 0:
        raise ValueError('Invalid threshold/transition/sigma')
    h, w = rgb.shape[:2]
    rgb8 = np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    lab = cv2.cvtColor(rgb8, cv2.COLOR_RGB2LAB).astype(np.float32)
    # Work in perceptual Lab units (OpenCV stores L at 0..255, a/b offset 128).
    lab[..., 0] *= 100.0 / 255.0
    lab[..., 1:] -= 128.0

    # Estimate paper from boundary pixels robustly; avoid relying on white or hue.
    border = max(3, min(h, w) // 30)
    boundary = np.zeros((h, w), dtype=bool)
    boundary[:border] = True
    boundary[-border:] = True
    boundary[:, :border] = True
    boundary[:, -border:] = True
    samples = lab[boundary]
    # Choose the densest population near the median, not the darkest paint.
    center = np.median(samples, axis=0)
    delta = np.linalg.norm(samples - center, axis=1)
    reliable = samples[delta <= np.percentile(delta, 65)]
    if reliable.size < 12:
        raise RuntimeError('Not enough border samples to estimate paper')
    center = np.median(reliable, axis=0)
    deviations = np.linalg.norm(reliable - center, axis=1)
    noise = max(1.0, float(np.percentile(deviations, 85)))

    # Spatially varying background, estimated only from samples resembling paper.
    raw_distance = np.linalg.norm(lab - center, axis=2)
    paper = raw_distance < max(noise * 2.2, 5.0)
    weight = paper.astype(np.float32)
    # Normalize spatial scale to image size without changing image dimensions.
    sigma = min(float(sigma_papel), max(5.0, min(h, w) / 3.0))
    denom = gaussian_filter(weight, sigma=sigma) + 1e-5
    background = np.empty_like(lab)
    for c in range(3):
        background[..., c] = gaussian_filter(lab[..., c] * weight, sigma=sigma) / denom

    difference = np.linalg.norm(lab - background, axis=2)
    difference = cv2.GaussianBlur(difference, (0, 0), 0.8)
    # Noise-adjusted sensitivity; user threshold is expressed in delta-E units.
    onset = max(float(threshold), noise * 1.6)
    alpha = np.clip((difference - onset) / float(transition), 0, 1)

    # Keep disconnected painted elements, but suppress tiny paper-noise islands.
    probable = (alpha > 0.22).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(probable, 8)
    minimum_area = max(9, int(h * w * 0.000008))
    retained = np.zeros((h, w), np.uint8)
    for n in range(1, count):
        if stats[n, cv2.CC_STAT_AREA] >= minimum_area:
            retained[labels == n] = 1
    if count <= 1 or not retained.any():
        raise RuntimeError('No significant pigment detected')
    # Allow graded edges near retained regions, not across the whole paper.
    nearby = cv2.dilate(retained, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    alpha *= nearby
    # Strong pigment stays fully visible; do not force pale interior to full alpha.
    alpha[difference >= onset + transition * 1.3] = 1.0
    return alpha.astype(np.float32)
