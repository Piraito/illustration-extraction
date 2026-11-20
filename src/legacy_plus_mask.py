"""Conservative, diagnostic-only enhancement of the legacy watercolor mask.

This module must not change original CMYK pixels, ICC, or the legacy alpha.
It makes a proposal that can ONLY raise alpha at chromatically supported pixels
near existing legacy artwork. It does not extend alpha using blurred color or
a distance-based opacity taper.
"""
import cv2
import numpy as np


def propose_legacy_plus(rgb, legacy_alpha, chroma_threshold=4.0,
                        chroma_span=8.0, neighborhood_px=7):
    """Return (proposed alpha, added alpha) for inspection, not production.

    Distances use OpenCV Lab a/b units; threshold is empirical and must be
    validated on real paper scans, not treated as a calibrated Delta-E.
    """
    if (rgb.ndim != 3 or rgb.shape[2] != 3 or
            legacy_alpha.shape != rgb.shape[:2]):
        raise ValueError('RGB and legacy mask dimensions are incompatible')
    if chroma_threshold < 0 or chroma_span <= 0 or neighborhood_px < 0:
        raise ValueError('Invalid proposal parameters')
    if not np.isfinite(rgb).all() or not np.isfinite(legacy_alpha).all():
        raise ValueError('Nonfinite input')

    h, w = legacy_alpha.shape
    rgb8 = np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    lab = cv2.cvtColor(rgb8, cv2.COLOR_RGB2LAB).astype(np.float32)
    border = max(3, min(h, w) // 30)
    samples = np.concatenate([
        lab[:border].reshape(-1, 3),
        lab[-border:].reshape(-1, 3),
        lab[:, :border].reshape(-1, 3),
        lab[:, -border:].reshape(-1, 3),
    ])
    mid = np.median(samples, axis=0)
    dev = np.linalg.norm(samples - mid, axis=1)
    good = samples[dev <= np.percentile(dev, 65)]
    paper = np.median(good, axis=0)
    # Chroma-only evidence avoids treating mild paper shadows as pigment.
    chroma_distance = np.linalg.norm(lab[..., 1:] - paper[1:], axis=2)
    baseline = np.clip((chroma_distance - chroma_threshold) / chroma_span, 0, 1)

    alpha = np.clip(legacy_alpha.astype(np.float32), 0, 1)
    # Only consider pixels adjoining already retained paint, not isolated
    # chromatic dust in the surrounding paper.
    seed = (alpha >= .08).astype(np.uint8)
    diameter = 2 * neighborhood_px + 1
    if neighborhood_px:
        nearby = cv2.dilate(
            seed, cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (diameter, diameter))).astype(bool)
    else:
        nearby = seed.astype(bool)

    # No smoothing of chroma and no alpha based on distance. The proposal
    # cannot erase anything the legacy mask already contains.
    proposal = np.maximum(alpha, np.where(nearby, baseline, 0))
    addition = proposal - alpha
    return proposal.astype(np.float32), addition.astype(np.float32)
