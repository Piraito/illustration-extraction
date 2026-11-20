#!/usr/bin/env python3
"""Conservative chromatic probe against legacy; NEVER modifies TIFF or CMYK."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from extract_illustrations import extraer, leer


def chroma_probe(rgb, legacy_alpha, paper_percentile=99.5, ramp=4.0):
    """Diagnostic-only: local a/b Lab contrast exceeding observed border noise."""
    if rgb.ndim != 3 or rgb.shape[2] != 3 or legacy_alpha.shape != rgb.shape[:2]:
        raise ValueError('RGB and legacy alpha dimensions do not agree')
    if not 90 <= paper_percentile <= 100 or ramp <= 0:
        raise ValueError('Invalid paper percentile or ramp')
    h, w = rgb.shape[:2]
    img8 = np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    lab = cv2.cvtColor(img8, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab[..., 1:] -= 128
    border_width = max(3, min(h, w) // 30)
    border = np.zeros((h, w), dtype=bool)
    border[:border_width] = border[-border_width:] = True
    border[:, :border_width] = border[:, -border_width:] = True
    paper_center = np.median(lab[border, 1:], axis=0)
    chroma = np.linalg.norm(lab[..., 1:] - paper_center, axis=2)
    noise_threshold = float(np.percentile(chroma[border], paper_percentile))
    candidate = np.clip((chroma - noise_threshold) / ramp, 0, 1).astype(np.float32)
    # An exploratory additive alpha: never changes preexisting legacy pixels.
    combined = np.maximum(legacy_alpha, candidate)
    added = combined - legacy_alpha
    # Border error is a warning, not a guarantee for all blank paper.
    report = {
        'paper_reference_ab': [round(float(x), 3) for x in paper_center],
        'paper_percentile': paper_percentile,
        'paper_threshold_ab_distance': round(noise_threshold, 3),
        'ramp': ramp,
        'legacy_nonzero_fraction': round(float((legacy_alpha > .05).mean()), 5),
        'combined_nonzero_fraction': round(float((combined > .05).mean()), 5),
        'added_alpha_gt_005_fraction': round(float((added > .05).mean()), 5),
        'border_added_alpha_gt_005_fraction': round(float((added[border] > .05).mean()), 5),
        'mean_added_alpha': round(float(added.mean()), 5),
        'warning': 'Diagnostic experiment only: border statistics cannot prove paper/pigment separation.',
    }
    return chroma, candidate, combined, added, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origen', type=Path, help='PSD/JPG CMYK original')
    parser.add_argument('salida', type=Path, help='New, empty diagnostic folder')
    parser.add_argument('--magick', default='convert')
    parser.add_argument('--paper-percentile', type=float, default=99.5)
    parser.add_argument('--ramp', type=float, default=4.)
    args = parser.parse_args()
    if not args.origen.is_file():
        parser.error('Source file does not exist')
    if args.salida.exists() and any(args.salida.iterdir()):
        parser.error('Output directory is not empty; choose a new one')
    _, rgb, _, _ = leer(args.origen, args.magick)
    _, legacy = extraer(rgb)
    chroma, candidate, combined, added, report = chroma_probe(
        rgb, legacy, args.paper_percentile, args.ramp)
    report['source'] = str(args.origen)
    args.salida.mkdir(parents=True, exist_ok=True)
    visuals = {
        '01_legacy_alpha.png': legacy,
        '02_candidato_cromatico.png': candidate,
        '03_combinado_experimental.png': combined,
        '04_alfa_anadido.png': added,
        '05_distancia_cromatica.png': chroma / max(1., float(np.percentile(chroma, 99))),
    }
    for filename, arr in visuals.items():
        Image.fromarray(np.rint(np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(
            args.salida / filename)
    (args.salida / 'informe.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Diagnostic saved to {args.salida}')


if __name__ == '__main__':
    main()
