#!/usr/bin/env python3
"""Inspect masks on a real CMYK/ICC scan without changing extraction outputs.

Outputs are sRGB diagnostic PNGs, not print-ready replacements for source PSD.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from extract_illustrations import extraer, leer
from adaptive_mask import adaptive_alpha
from legacy_plus_mask import propose_legacy_plus


def to_u8(arr):
    return np.rint(np.clip(arr, 0, 1) * 255).astype(np.uint8)


def paper_reference(rgb):
    """Robust Lab estimate from the scan boundary; diagnostic only."""
    lab = cv2.cvtColor(to_u8(rgb), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab[..., 0] *= 100 / 255
    lab[..., 1:] -= 128
    h, w = rgb.shape[:2]
    width = max(3, min(h, w) // 30)
    border = np.zeros((h, w), dtype=bool)
    border[:width, :] = border[-width:, :] = True
    border[:, :width] = border[:, -width:] = True
    samples = lab[border]
    center = np.median(samples, axis=0)
    distances = np.linalg.norm(samples - center, axis=1)
    chosen = samples[distances <= np.percentile(distances, 65)]
    center = np.median(chosen, axis=0)
    return lab, center, border


def describe(rgb, lab, reference, legacy, adaptive, selection):
    count = int(np.count_nonzero(selection))
    if not count:
        return {'pixels': 0}
    diff = legacy[selection] - adaptive[selection]
    dist = np.linalg.norm(lab[selection] - reference, axis=1)
    return {
        'pixels': count,
        'rgb_mean_0_255': [round(float(x), 2) for x in
                            (rgb[selection].mean(axis=0) * 255)],
        'lab_mean': [round(float(x), 2) for x in lab[selection].mean(axis=0)],
        'lab_distance_to_border_median': round(float(np.median(dist)), 2),
        'lab_distance_to_border_p90': round(float(np.percentile(dist, 90)), 2),
        'legacy_alpha_mean': round(float(legacy[selection].mean()), 4),
        'adaptive_alpha_mean': round(float(adaptive[selection].mean()), 4),
        'legacy_minus_adaptive_mean': round(float(diff.mean()), 4),
    }


def diagnostics(rgb, regions=(), sigma=100, umbral=5.5, anchura=19):
    """Return images/report for comparison. Never writes original CMYK or TIFF."""
    _, legacy = extraer(rgb, sigma, umbral, anchura)
    adaptive = adaptive_alpha(rgb, sigma, umbral, anchura)
    legacy_plus, addition = propose_legacy_plus(rgb, legacy)
    lab, reference, border = paper_reference(rgb)
    disagreement = legacy - adaptive
    h, w = legacy.shape

    # These maps are measured diagnostics, NOT the intermediate signal used by
    # either algorithm. In particular, the Lab distance is a color contrast
    # proxy, not an alpha estimate.
    color_distance = np.linalg.norm(lab - reference, axis=2)
    scale = max(8., float(np.percentile(color_distance, 99)))
    color_gray = to_u8(color_distance / scale)

    # Signed comparison: red=legacy retains more, blue=adaptive retains more.
    positive = to_u8(np.maximum(disagreement, 0))
    negative = to_u8(np.maximum(-disagreement, 0))
    difference_rgb = np.zeros((h, w, 3), dtype=np.uint8)
    difference_rgb[..., 0] = positive
    difference_rgb[..., 2] = negative

    # Identical sRGB source shown over checkerboard for honest visual comparison.
    yy, xx = np.ogrid[:h, :w]
    checker = np.where(((yy // 24 + xx // 24) % 2) == 0,
                       230, 190).astype(np.uint8)
    backdrop = np.broadcast_to(checker[..., None], (h, w, 3))
    original = to_u8(rgb).astype(np.float32)

    def composite(alpha):
        return np.rint(original * alpha[..., None] +
                       backdrop * (1 - alpha[..., None])).astype(np.uint8)

    images = {
        'original_srgb.png': to_u8(rgb),
        'legacy_alpha.png': to_u8(legacy),
        'adaptive_alpha.png': to_u8(adaptive),
        'legacy_plus_alpha_experimental.png': to_u8(legacy_plus),
        'legacy_plus_adicion_experimental.png': to_u8(addition),
        'diferencia_rojo_legacy_azul_adaptive.png': difference_rgb,
        'distancia_lab_papel.png': color_gray,
        'legacy_sobre_damero.png': composite(legacy),
        'adaptive_sobre_damero.png': composite(adaptive),
        'legacy_plus_sobre_damero_experimental.png': composite(legacy_plus),
    }
    masks = {
        'papel_borde': border,
        'ambos_transparentes': (legacy < .05) & (adaptive < .05),
        'ambos_opacos': (legacy > .95) & (adaptive > .95),
        'legacy_conserva_mas': disagreement > .25,
        'adaptive_conserva_mas': disagreement < -.25,
        'transiciones_legacy': (legacy > .05) & (legacy < .95),
    }
    for name, x, y, rw, rh in regions:
        if rw <= 0 or rh <= 0 or x < 0 or y < 0 or x + rw > w or y + rh > h:
            raise ValueError(f'Región fuera de imagen: {name}:{x}:{y}:{rw}:{rh}')
        if name in masks:
            raise ValueError(f'Nombre de región reservado: {name}')
        m = np.zeros((h, w), bool)
        m[y:y+rh, x:x+rw] = True
        masks[name] = m
    report = {
        'width': w, 'height': h,
        'paper_border_lab_median': [round(float(v), 2) for v in reference],
        'lab_distance_scale_p99': round(scale, 2),
        'fraction_legacy_alpha_gt_005': round(float((legacy > .05).mean()), 5),
        'fraction_adaptive_alpha_gt_005': round(float((adaptive > .05).mean()), 5),
        'fraction_legacy_plus_alpha_gt_005': round(float((legacy_plus > .05).mean()), 5),
        'fraction_legacy_plus_added_alpha_mean': round(float(addition.mean()), 6),
        'regions': {
            key: describe(rgb, lab, reference, legacy, adaptive, mask)
            for key, mask in masks.items()
        },
        'notes': [
            'Visualizations are color-managed sRGB diagnostic PNGs, not CMYK originals.',
            'Red means legacy alpha exceeds adaptive; blue means the opposite.',
            'Lab map is distance to border paper reference, not either method internal signal.',
            'Automatic regions are heuristics; they do not establish ground truth.',
            'legacy_plus is diagnostic-only, uses raw local chroma and never decreases legacy alpha.',
        ],
    }
    return images, report


def parse_region(value):
    try:
        name, x, y, w, h = value.split(':')
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            raise ValueError
        return name, int(x), int(y), int(w), int(h)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            'Usar NOMBRE:X:Y:ANCHO:ALTO') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origen', type=Path, help='PSD o JPG CMYK individual')
    parser.add_argument('salida', type=Path, help='Carpeta nueva de diagnóstico')
    parser.add_argument('--magick', default='convert')
    parser.add_argument('--region', type=parse_region, action='append', default=[],
                        help='Región de interés NOMBRE:X:Y:ANCHO:ALTO; repetible')
    parser.add_argument('--sigma-papel', type=float, default=100)
    parser.add_argument('--umbral', type=float, default=5.5)
    parser.add_argument('--anchura', type=float, default=19)
    args = parser.parse_args()
    if not args.origen.is_file():
        parser.error('No existe el archivo de origen')
    if args.salida.exists() and any(args.salida.iterdir()):
        parser.error('La carpeta de diagnóstico ya contiene archivos: usar otra')
    _, rgb, _, _ = leer(args.origen, args.magick)
    images, report = diagnostics(
        rgb, args.region, args.sigma_papel, args.umbral, args.anchura)
    report['origin'] = str(args.origen)
    report['parameters'] = dict(sigma_papel=args.sigma_papel,
                                umbral=args.umbral, anchura=args.anchura)
    args.salida.mkdir(parents=True, exist_ok=True)
    for name, pixels in images.items():
        Image.fromarray(pixels).save(args.salida / name)
    (args.salida / 'informe.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8')
    print(f'Diagnóstico: {args.salida} ({len(images)} PNG + informe.json)')


if __name__ == '__main__':
    main()
