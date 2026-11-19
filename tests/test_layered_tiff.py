"""Structural test for an editable CMYK layer-mask TIFF.

Run: python -m unittest discover -s tests -p 'test_layered_tiff.py'
"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


class LayeredTiffTest(unittest.TestCase):
    def test_original_cmyk_and_mask_roundtrip(self):
        from layered_tiff import guardar_tiff_editable
        from psdtags import TiffImageSourceData, PsdChannelId

        h, w = 64, 96
        rng = np.random.default_rng(14)
        cmyk = rng.integers(0, 256, (h, w, 4), dtype=np.uint8)
        alpha = np.broadcast_to(np.linspace(0, 1, w, dtype=np.float32), (h, w))
        # Test binary ICC payload structurally, without relying on a system profile.
        # tifffile embeds ICC tag verbatim; color-management behavior not tested here.
        icc = bytearray(128)
        icc[0:4] = (128).to_bytes(4, 'big')
        icc[16:20] = b'CMYK'
        icc[36:40] = b'acsp'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test_editable.tif'
            guardar_tiff_editable(path, cmyk, alpha, bytes(icc), (300, 300))
            with tifffile.TiffFile(path) as tif:
                pixels = tif.pages[0].asarray()
                self.assertTrue(np.array_equal(pixels[..., :4], cmyk))
                self.assertTrue(np.array_equal(tif.pages[0].tags['InterColorProfile'].value, bytes(icc)))
            layered = TiffImageSourceData.fromtiff(str(path))
            channels = {c.channelid: c.data for c in layered.layers.layers[0].channels}
            self.assertTrue(np.array_equal(255 - channels[PsdChannelId.CHANNEL3], cmyk[..., 3]))
            self.assertTrue(np.array_equal(
                channels[PsdChannelId.USER_LAYER_MASK],
                np.rint(alpha * 255).astype(np.uint8),
            ))


if __name__ == '__main__':
    unittest.main()
