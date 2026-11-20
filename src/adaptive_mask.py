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
    but cannot distinguish very pale pigment from similar paper with certainty.\n    Preserves enclosed pale regions spatially, including paper-colored portions.
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
    # Construct an envelope from the *strong* pigment. Close small gaps and
    # fill enclosed areas: pale/white interiors must not become transparent.
    # This is intentionally conservative: a little surrounding paper is better
    # than destroying original artwork. Spatial scale tracks image dimensions.
    close_diameter = max(9, int(round(min(h, w) * 0.025)) | 1)
    close_diameter = min(close_diameter, 101)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (close_diameter, close_diameter))
    joined = cv2.morphologyEx(retained, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(
        joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    envelope = np.zeros_like(joined)
    cv2.drawContours(envelope, contours, -1, 1, cv2.FILLED)
    # Protect the original from 2px inside the envelope, with a soft transition
    # at its outline; do not rely on the color of enclosed pale washes.
    inner = cv2.distanceTransform(envelope, cv2.DIST_L2, 5)
    protected = np.clip((inner - 0.5) / 2.0, 0, 1)
    # An outer watercolor wash is often broader than the sharply painted body.
    # Fixed-radius dilation loses it; evaluate low-frequency color deviations
    # against the *border paper* and taper the eligible exterior with distance.
    # Spatial smoothing rejects high-frequency paper grain, while the broad,
    # gradual reach avoids a hard crop around the main subject.
    distance_outside = cv2.distanceTransform(
        (1 - envelope).astype(np.uint8), cv2.DIST_L2, 5)
    reach = max(18.0, min(h, w) * 0.22)
    vicinity = np.clip(1.0 - distance_outside / reach, 0, 1)
    smooth_sigma = max(2.0, min(h, w) * 0.012)
    smooth_lab = cv2.GaussianBlur(lab, (0, 0), smooth_sigma)
    # Compared with the near-white border reference, chromatic displacement
    # is often more informative than a very small luminance difference.
    smooth_delta = smooth_lab - center
    wash_signal = np.sqrt(
        (0.35 * smooth_delta[..., 0]) ** 2
        + smooth_delta[..., 1] ** 2
        + smooth_delta[..., 2] ** 2)
    paper_noise = max(0.8, noise * 0.6)
    wash_confidence = np.clip(
        (wash_signal - paper_noise) / max(3.0, transition * 0.65), 0, 1)
    # Do not extend the wash response into unbounded paper, even if paper
    # illumination differs slightly from that of the scan's border.
    wash = wash_confidence * vicinity
    exterior = np.maximum(alpha * vicinity, wash)
    result = np.maximum(protected, exterior)
    return np.clip(result, 0, 1).astype(np.float32)
