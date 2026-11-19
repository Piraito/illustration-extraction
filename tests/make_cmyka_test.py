#!/usr/bin/env python3
"""Diagnostic TIFF CMYK + unassociated alpha for Scribus (not a production extractor)."""
import argparse
from pathlib import Path
import numpy as np
import tifffile

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output', type=Path)
    ap.add_argument('--icc', type=Path, help='Embedded source CMYK ICC extracted from a PSD')
    args = ap.parse_args()
    h, w = 640, 960
    yy, xx = np.mgrid[:h, :w]
    ink = np.zeros((h, w, 4), dtype=np.uint8)
    swatches = [(75, 0, 0, 0), (0, 75, 0, 0), (0, 0, 75, 0),
                (0, 0, 0, 75), (35, 50, 0, 15)]
    for i, cmyk in enumerate(swatches):
        ink[150:480, 55 + 174*i:192 + 174*i] = cmyk
    d = np.sqrt(((xx-480)/445)**2 + ((yy-320)/278)**2)
    alpha = np.rint(np.clip((1.05-d)/.22, 0, 1)*255).astype(np.uint8)
    alpha[255:345, 390:570] = 0
    ink[255:345, 390:570] = (80, 40, 20, 15)
    pixels = np.dstack((ink, alpha))
    icc = args.icc.read_bytes() if args.icc else None
    if icc and (len(icc)<128 or icc[36:40]!=b'acsp' or icc[16:20]!=b'CMYK'):
        ap.error('Expected a valid CMYK ICC profile')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(args.output, pixels, photometric='separated',
                     planarconfig='contig', extrasamples=['unassalpha'],
                     iccprofile=icc, resolution=(300, 300),
                     resolutionunit='inch', compression='deflate', metadata=None)
    with tifffile.TiffFile(args.output) as tif:
        page = tif.pages[0]
        assert page.photometric == tifffile.PHOTOMETRIC.SEPARATED
        assert page.samplesperpixel == 5
        assert list(page.extrasamples) == [tifffile.EXTRASAMPLE.UNASSALPHA]
        assert np.array_equal(page.asarray(), pixels), 'CMYK/alpha modified'
        assert bool(page.tags.get('InterColorProfile')) == bool(icc)
    print(f'OK: {args.output} (960x640, CMYK+alpha, 8-bit)')
    print('ICC:', args.icc if icc else 'none — transparency-only diagnostic')

if __name__ == '__main__':
    main()
