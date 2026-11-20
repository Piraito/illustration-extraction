#!/usr/bin/env python3
"""Extracción experimental de ilustraciones escaneadas por lotes.

Lee JPG/JPEG y PSD CMYK de 8 bits; conserva los cuatro canales CMYK,
perfil ICC original, dimensiones y resolución. Añade un alfa no premultiplicado
y exporta TIFF CMYK+A. El RGB temporal solo sirve para calcular la máscara.

Algoritmo EXPERIMENTAL calibrado inicialmente para acuarelas de papel claro.
PSD: ImageMagick extrae la composición a TIFF; comprobar los Smart Objects.
No procesa RGB ni HDR en esta etapa: falla explícitamente.

Dependencias: numpy, scipy, opencv-python, Pillow, tifffile, ImageMagick 6/7.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from io import BytesIO
from collections import Counter
import struct
import tifffile
from PIL import Image, ImageOps, ImageCms
from scipy.ndimage import gaussian_filter

EXTS = {'.jpg', '.jpeg', '.psd'}


def perfil_psd(path: Path) -> bytes:
    """Lee ICC (recurso Photoshop 0x040F) directamente del PSD original."""
    with path.open('rb') as stream:
        if stream.read(4) != b'8BPS':
            raise RuntimeError('No es un PSD válido')
        stream.seek(26)
        color_length = struct.unpack('>I', stream.read(4))[0]
        stream.seek(color_length, 1)
        resources_length = struct.unpack('>I', stream.read(4))[0]
        end = stream.tell() + resources_length
        while stream.tell() < end:
            if stream.read(4) != b'8BIM':
                raise RuntimeError('Recurso PSD inesperado')
            resource_id = struct.unpack('>H', stream.read(2))[0]
            name_length = stream.read(1)[0]
            stream.seek(name_length + (1 if (name_length + 1) % 2 else 0), 1)
            size = struct.unpack('>I', stream.read(4))[0]
            payload = stream.read(size)
            if size % 2:
                stream.seek(1, 1)
            if resource_id == 0x040F:
                return payload
    raise RuntimeError('PSD sin perfil ICC incrustado')


def leer(path: Path, magick: str):
    """Devuelve canales CMYK intactos, perfil ICC original y resolución."""
    if path.suffix.lower() != '.psd':
        with Image.open(path) as im:
            if im.mode != 'CMYK':
                raise RuntimeError(f'Se requiere CMYK, imagen {im.mode}; soporte RGB pendiente')
            icc = im.info.get('icc_profile')
            dpi = im.info.get('dpi')
            cmyk = np.asarray(im, dtype=np.uint8).copy()
    else:
        icc = perfil_psd(path)
        with tempfile.TemporaryDirectory(prefix='illustration_') as td:
            dest = Path(td) / 'compuesto.tif'
            cmd = [magick, f'{path}[0]', '-depth', '8', '-compress', 'none', str(dest)]
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode or not dest.exists():
                raise RuntimeError('Error al leer PSD: ' + p.stderr.strip()[-1200:])
            with Image.open(dest) as im:
                if im.mode != 'CMYK':
                    raise RuntimeError(f'PSD compuesto no CMYK ({im.mode})')
                cmyk = np.asarray(im, dtype=np.uint8).copy()
                dpi = im.info.get('dpi')

    if not icc or len(icc) < 128 or icc[36:40] != b'acsp' or icc[16:20] != b'CMYK':
        raise RuntimeError('ICC original ausente o no corresponde a CMYK')
    try:
        source = ImageCms.ImageCmsProfile(BytesIO(icc))
        srgb = ImageCms.createProfile('sRGB')
        rgb_img = ImageCms.profileToProfile(
            Image.fromarray(cmyk, mode='CMYK'), source, srgb,
            outputMode='RGB')
    except Exception as exc:
        raise RuntimeError(f'No se pudo convertir temporalmente a RGB mediante ICC: {exc}') from exc
    rgb = np.asarray(rgb_img, dtype=np.float32) / 255.0
    return cmyk, rgb, icc, dpi


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


def guardar_tiff(path, cmyk, alpha, icc, dpi):
    """Escribe cinco canales sin alterar los cuatro CMYK originales."""
    a = np.rint(np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    pixels = np.dstack((cmyk, a))
    options = dict(photometric='separated', planarconfig='contig',
                   extrasamples=['unassalpha'], iccprofile=icc,
                   compression='deflate', metadata=None)
    if dpi and len(dpi) >= 2 and dpi[0] > 0 and dpi[1] > 0:
        options.update(resolution=(float(dpi[0]), float(dpi[1])),
                       resolutionunit='inch')
    tifffile.imwrite(path, pixels, **options)
    with tifffile.TiffFile(path) as t:
        page = t.pages[0]
        check = page.asarray()
        if (page.samplesperpixel != 5 or
            list(page.extrasamples) != [tifffile.EXTRASAMPLE.UNASSALPHA] or
            not np.array_equal(check[:, :, :4], cmyk) or
            not np.array_equal(check[:, :, 4], a)):
            raise RuntimeError('No se verificó integridad CMYK y alfa del TIFF')
        profile = page.tags.get('InterColorProfile')
        if profile is None or profile.value != icc:
            raise RuntimeError('El ICC no coincide con el original')



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('entrada', type=Path)
    ap.add_argument('salida', type=Path)
    ap.add_argument('--magick', default='convert', help='Ejecutable ImageMagick (convert en Ubuntu; magick en IM7)')
    ap.add_argument('--recursivo', action='store_true')
    ap.add_argument('--solo-psd', action='store_true',
                    help='Procesar solo PSD, ignorando JPG/JPEG (incluidos RGB)')
    ap.add_argument('--export-mask', action='store_true',
                    help='Exportar además una máscara PNG de diagnóstico (desactivado por defecto)')
    ap.add_argument('--output-format', choices=('tiff-alpha', 'tiff-layer-mask', 'both'),
                    default='tiff-alpha', help='Formato(s) TIFF de salida')
    ap.add_argument('--mask-method', choices=('acuarela', 'legacy', 'adaptive', 'connected-wash'), default='acuarela',
                    help='Máscara: acuarela (recomendada y predeterminada); legacy es alias histórico')
    ap.add_argument('--sigma-papel', type=float, default=100)
    ap.add_argument('--umbral', type=float, default=5.5)
    ap.add_argument('--anchura', type=float, default=19)
    args = ap.parse_args()
    if not args.entrada.is_dir():
        ap.error('La carpeta de entrada no existe')
    if args.entrada.resolve() == args.salida.resolve():
        ap.error('Entrada y salida deben ser distintas')
    files = sorted(p for p in (args.entrada.rglob('*') if args.recursivo else args.entrada.iterdir())
                   if p.is_file() and p.suffix.lower() in ({'.psd'} if args.solo_psd else EXTS))
    args.salida.mkdir(parents=True, exist_ok=True)
    # Si 23.psd y 23.jpg coexisten, no deben generar ambos 23.tif.
    bases = Counter(str(p.relative_to(args.entrada).with_suffix('')).lower() for p in files)
    errores = []
    for i, src in enumerate(files, 1):
        rel = src.relative_to(args.entrada)
        base = rel.with_suffix('')
        if bases[str(base).lower()] > 1:
            base = base.with_name(base.name + '_' + src.suffix[1:].lower())
        dest = args.salida / base.with_suffix('.tif')
        editable = dest.with_name(dest.stem + '_editable.tif')
        outputs = ([dest] if args.output_format == 'tiff-alpha' else
                   [editable] if args.output_format == 'tiff-layer-mask' else
                   [dest, editable])
        dest.parent.mkdir(parents=True, exist_ok=True)
        if any(p.exists() for p in outputs):
            print(f'[{i}/{len(files)}] OMITIDO (ya existe una salida): {src.name}')
            continue
        try:
            cmyk, rgb, icc, dpi = leer(src, args.magick)
            if args.mask_method == 'adaptive':
                from adaptive_mask import adaptive_alpha
                alpha = adaptive_alpha(rgb, args.sigma_papel, args.umbral, args.anchura)
            else:
                _, alpha = extraer(rgb, args.sigma_papel, args.umbral, args.anchura)
                if args.mask_method == 'connected-wash':
                    from connected_wash import connected_wash
                    alpha, _, info = connected_wash(rgb, alpha)
                    print(f'  connected-wash experimental: {info}')
            created = []
            try:
                if dest in outputs:
                    guardar_tiff(dest, cmyk, alpha, icc, dpi)
                    created.append(dest)
                if editable in outputs:
                    from layered_tiff import guardar_tiff_editable
                    guardar_tiff_editable(editable, cmyk, alpha, icc, dpi)
                    created.append(editable)
            except Exception:
                for output in outputs:
                    if output.exists():
                        output.unlink()
                raise
            if args.export_mask:
                mpath = dest.with_name(dest.stem + '_mascara.png')
                if not cv2.imwrite(str(mpath), np.rint(alpha*255).astype(np.uint8)):
                    raise RuntimeError('No se pudo escribir la máscara PNG')
            print(f'[{i}/{len(files)}] OK {src.name}: {rgb.shape[1]}x{rgb.shape[0]} -> {", ".join(str(p) for p in outputs)}')
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
