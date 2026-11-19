#!/usr/bin/env python3
"""Extracción experimental de ilustraciones escaneadas por lotes.

Lee JPG/JPEG y PSD (composición visible PSD[0] de ImageMagick), sin cambiar
las dimensiones. Exporta PNG RGBA de 8 bits/canal y máscaras de 8 bits.

IMPORTANTE: el algoritmo está calibrado inicialmente para una acuarela con
papel claro y aguadas rosas. El RGB se corrige cerca de los bordes
semitransparentes: NO se ha decidido aún el modo de conservación de RGB.
Las imágenes CMYK se convierten a sRGB mediante su perfil ICC incrustado.
El soporte de PSD flotantes/HDR queda pendiente de una implementación aparte.

Dependencias: numpy, scipy, opencv-python, Pillow, ImageMagick 6/7.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from io import BytesIO
from collections import Counter
from PIL import Image, ImageOps, ImageCms
from scipy.ndimage import gaussian_filter

EXTS = {'.jpg', '.jpeg', '.psd'}


def convertir_a_rgb(im: Image.Image) -> np.ndarray:
    """Convierte el compuesto al espacio sRGB usando ICC, sin conversiones CMYK ingenuas."""
    perfil = im.info.get('icc_profile')
    if im.mode in ('CMYK', 'RGB') and perfil:
        origen = ImageCms.ImageCmsProfile(BytesIO(perfil))
        destino = ImageCms.createProfile('sRGB')
        rgb = ImageCms.profileToProfile(im, origen, destino, outputMode='RGB')
    elif im.mode == 'CMYK':
        raise RuntimeError('CMYK sin perfil ICC: conversión a RGB no segura')
    elif im.mode in ('RGB', 'RGBA'):
        rgb = im.convert('RGB')  # RGB sin ICC: se asume sRGB
    else:
        raise RuntimeError(f'Modo de imagen no soportado: {im.mode}')
    return np.asarray(rgb, dtype=np.float32) / 255.0


def leer(path: Path, magick: str) -> np.ndarray:
    if path.suffix.lower() != '.psd':
        with Image.open(path) as im:
            return convertir_a_rgb(ImageOps.exif_transpose(im))

    # Extrae el compuesto guardado por Photoshop, conservando el ICC.
    # ImageMagick Q16 sirve para PSD CMYK de 8 bits, pero no valida HDR.
    with tempfile.TemporaryDirectory(prefix='illustration_') as td:
        dest = Path(td) / 'compuesto.tif'
        cmd = [magick, f'{path}[0]', '-depth', '8', '-compress', 'none', str(dest)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode or not dest.exists():
            raise RuntimeError('Error al leer PSD: ' + p.stderr.strip()[-1200:])
        with Image.open(dest) as im:
            return convertir_a_rgb(im)


def extraer(rgb: np.ndarray, sigma_papel=100, umbral=5.5, anchura=19,
            proteccion_borde=14, proteccion_transicion=38) -> tuple[np.ndarray, np.ndarray]:
    # Parámetros de máscara originalmente calibrados en unidades equivalentes a 8 bits.
    im = (rgb * 255).astype(np.float32)
    h, w = im.shape[:2]
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    pink = np.maximum(0, r-g) + np.maximum(0, b-g)*.6
    paper = (g > 238) & (r > 239) & (pink < 8) & ((r-b) < 23)
    if paper.mean() < .005:
        raise RuntimeError('No se detectaron suficientes muestras de papel claro')
    bg = np.empty_like(im)
    wt = gaussian_filter(paper.astype(np.float32), sigma=sigma_papel) + 1e-6
    for k in range(3):
        bg[:, :, k] = gaussian_filter(im[:, :, k]*paper, sigma=sigma_papel)/wt
    delta = bg-im
    p = np.maximum(0, (r-g)-(bg[:, :, 0]-bg[:, :, 1]))
    q = np.maximum(0, (b-g)-(bg[:, :, 2]-bg[:, :, 1]))
    dark = np.maximum(0, delta.mean(axis=2))
    signal = cv2.GaussianBlur(np.maximum(p*.95+q*.4, dark*.8), (0, 0), 1.3)
    alpha = np.clip((signal-umbral)/anchura, 0, 1)
    region = (alpha > .20).astype(np.uint8)
    region = cv2.morphologyEx(region, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(region)
    if n < 2:
        raise RuntimeError('No se detectó una región coloreada principal')
    major = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    region = (labels == major).astype(np.uint8)
    padded = cv2.copyMakeBorder(region, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inv = (1-padded).astype(np.uint8)
    floodmask = np.zeros((h+4, w+4), np.uint8)
    cv2.floodFill(inv, floodmask, (0, 0), 2)
    holes = (inv[1:-1, 1:-1] == 1).astype(np.uint8)
    region = np.maximum(region, holes)
    inside = cv2.distanceTransform(region, cv2.DIST_L2, 5)
    protection = np.clip((inside-proteccion_borde)/proteccion_transicion, 0, 1)
    alpha = alpha*(1-protection)+protection
    safe = np.maximum(alpha, .04)
    fg = np.clip((im-(1-alpha[..., None])*bg)/safe[..., None], 0, 255)/255
    fg[alpha >= .999] = rgb[alpha >= .999]
    return fg.astype(np.float32), alpha.astype(np.float32)


def guardar_png8(path, rgb, alpha):
    rgba = np.dstack([rgb, alpha])
    u8 = np.rint(np.clip(rgba, 0, 1)*255).astype(np.uint8)
    if not cv2.imwrite(str(path), u8[:, :, [2, 1, 0, 3]]):
        raise RuntimeError(f'Error escribiendo {path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('entrada', type=Path)
    ap.add_argument('salida', type=Path)
    ap.add_argument('--magick', default='convert', help='Ejecutable ImageMagick (convert en Ubuntu; magick en IM7)')
    ap.add_argument('--recursivo', action='store_true')
    ap.add_argument('--sigma-papel', type=float, default=100)
    ap.add_argument('--umbral', type=float, default=5.5)
    ap.add_argument('--anchura', type=float, default=19)
    args = ap.parse_args()
    if not args.entrada.is_dir():
        ap.error('La carpeta de entrada no existe')
    if args.entrada.resolve() == args.salida.resolve():
        ap.error('Entrada y salida deben ser distintas')
    files = sorted(p for p in (args.entrada.rglob('*') if args.recursivo else args.entrada.iterdir())
                   if p.is_file() and p.suffix.lower() in EXTS)
    args.salida.mkdir(parents=True, exist_ok=True)
    # Si 23.psd y 23.jpg coexisten, no deben generar ambos 23.png.
    bases = Counter(str(p.relative_to(args.entrada).with_suffix('')).lower() for p in files)
    errores = []
    for i, src in enumerate(files, 1):
        rel = src.relative_to(args.entrada)
        base = rel.with_suffix('')
        if bases[str(base).lower()] > 1:
            base = base.with_name(base.name + '_' + src.suffix[1:].lower())
        dest = args.salida / base.with_suffix('.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f'[{i}/{len(files)}] OMITIDO (ya existe): {dest}')
            continue
        try:
            rgb = leer(src, args.magick)
            fg, alpha = extraer(rgb, args.sigma_papel, args.umbral, args.anchura)
            guardar_png8(dest, fg, alpha)
            mpath = dest.with_name(dest.stem + '_mascara.png')
            cv2.imwrite(str(mpath), np.rint(alpha*255).astype(np.uint8))
            print(f'[{i}/{len(files)}] OK {src.name}: {rgb.shape[1]}x{rgb.shape[0]} -> {dest}')
        except Exception as exc:
            errores.append(f'{src}: {exc}')
            print(f'[{i}/{len(files)}] ERROR {src.name}: {exc}')
    if errores:
        log = args.salida / 'errores_procesamiento.txt'
        log.write_text('\n'.join(errores)+'\n', encoding='utf-8')
        print(f'Errores: {len(errores)}. Ver {log}')
        raise SystemExit(1)
    print(f'Terminados: {len(files)} archivos')


if __name__ == '__main__':
    main()
