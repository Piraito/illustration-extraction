"""Experimental chromatic region growing from legacy seeds (diagnostic only).

Unlike prior proposals, this does not use Gaussian blur, alpha feathering,
morphological dilation, or a distance-to-contour falloff. It labels connected
pixels whose *own* color differs from reference paper, then accepts only
components touched by reliable legacy mask pixels. No production TIFF changes.
"""
import cv2
import numpy as np


def connected_wash(rgb, legacy_alpha, threshold=None, alpha_span=8.0,
                   seed_alpha=0.60):
    """Return proposed alpha, added alpha, and diagnostic statistics.

    Lab a/b distances use the OpenCV 8-bit Lab encoding, not Delta-E 2000.
    A flat border reference is assumed; true edge-to-edge artwork needs a
    different reference strategy. Output never decreases legacy alpha.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3 or legacy_alpha.shape != rgb.shape[:2]:
        raise ValueError('RGB and legacy alpha dimensions differ')
    if not np.isfinite(rgb).all() or not np.isfinite(legacy_alpha).all():
        raise ValueError('Nonfinite input')
    if alpha_span <= 0 or not (0 < seed_alpha <= 1):
        raise ValueError('Invalid alpha span or seed threshold')
    if threshold is not None and threshold <= 0:
        raise ValueError('Chromatic threshold must be positive')

    h, w = legacy_alpha.shape
    rgb8 = np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    lab = cv2.cvtColor(rgb8, cv2.COLOR_RGB2LAB).astype(np.float32)
    b = max(3, min(h, w) // 30)
    samples = np.concatenate((
        lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3),
        lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3),
    ))
    median = np.median(samples, axis=0)
    initial_dist = np.linalg.norm(samples - median, axis=1)
    reference = np.median(
        samples[initial_dist <= np.percentile(initial_dist, 65)], axis=0)
    border_chroma = np.linalg.norm(samples[:, 1:] - reference[1:], axis=1)
    cutoff = (max(2.2, float(np.percentile(border_chroma, 95)) + 0.15)
              if threshold is None else float(threshold))
    distance = np.linalg.norm(lab[..., 1:] - reference[1:], axis=2)
    candidate = (distance > cutoff).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    legacy = np.clip(legacy_alpha.astype(np.float32), 0, 1)
    seeds = (legacy >= seed_alpha) & (candidate > 0)
    qualifying = np.unique(labels[seeds])
    qualifying = qualifying[qualifying > 0]
    accepted = np.zeros(count, dtype=bool)
    accepted[qualifying] = True
    accepted[0] = False
    # Exclude candidate components touching the scan border: their connection
    # to border paper is ambiguous and risks selecting a huge noise region.
    touching = np.unique(np.concatenate((
        labels[:b].ravel(), labels[-b:].ravel(),
        labels[:, :b].ravel(), labels[:, -b:].ravel(),
    )))
    accepted[touching] = False
    selected = accepted[labels]
    # Actual pixel chroma controls alpha. Connectedness only decides whether
    # that pixel belongs to the same color region as a legacy seed.
    chroma_alpha = np.clip((distance - cutoff) / alpha_span, 0, 1)
    proposal = np.maximum(legacy, np.where(selected, chroma_alpha, 0))
    addition = (proposal - legacy).astype(np.float32)
    info = {
        'border_reference_lab_encoded': [round(float(x), 2) for x in reference],
        'border_chroma_p95': round(float(np.percentile(border_chroma, 95)), 3),
        'candidate_cutoff': round(float(cutoff), 3),
        'connected_components_accepted': int(np.count_nonzero(accepted)),
        'new_pixels_alpha_gt_005': int(np.count_nonzero(
            (legacy <= .05) & (proposal > .05))),
        'added_alpha_mean': round(float(addition.mean()), 8),
        'note': 'No ground-truth validation; diagnostics only.',
    }
    return proposal.astype(np.float32), addition, info
