"""Synthetic checks of hue-neutral adaptive alpha. No production images needed."""
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from adaptive_mask import adaptive_alpha


class AdaptiveMaskTests(unittest.TestCase):
    def test_painted_islands_of_different_hues(self):
        h, w = 240, 320
        rng = np.random.default_rng(2026)
        noise = rng.normal(0, 0.002, (h, w, 1))
        rgb = np.clip(np.array([.95, .93, .88], np.float32)[None,None,:]
                      + noise, 0, 1).astype(np.float32)
        cv2.circle(rgb, (90, 120), 35, (.25, .65, .8), -1)
        cv2.circle(rgb, (225, 115), 31, (.7, .35, .2), -1)
        alpha = adaptive_alpha(rgb, sigma_papel=30)
        self.assertEqual(alpha.shape, (h, w))
        self.assertGreater(alpha[120, 90], .9)
        self.assertGreater(alpha[115, 225], .9)
        self.assertLess(alpha[15, 15], .08)
        self.assertGreater(len(np.unique(np.rint(alpha * 255))), 2)

    def test_preserves_green_and_yellow_not_only_pink(self):
        rgb = np.full((180, 240, 3), [.96, .94, .89], np.float32)
        cv2.rectangle(rgb, (45, 40), (105, 130), (.1, .55, .2), -1)
        cv2.rectangle(rgb, (135, 50), (200, 140), (.9, .6, .1), -1)
        alpha = adaptive_alpha(rgb, sigma_papel=25)
        self.assertGreater(alpha[70, 70], .9)
        self.assertGreater(alpha[70, 170], .9)
        self.assertLess(alpha[10, 10], .01)

    def test_invalid_image(self):
        with self.assertRaises(ValueError):
            adaptive_alpha(np.zeros((30, 30), np.float32))


if __name__ == '__main__':
    unittest.main()
