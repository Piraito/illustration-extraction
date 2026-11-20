"""Tests for the experimental, non-production chroma probe."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from chroma_probe import chroma_probe


class ChromaProbeTests(unittest.TestCase):
    def test_legacy_never_reduced_and_color_probe_stays_local(self):
        rgb = np.full((120, 160, 3), [.96, .94, .90], dtype=np.float32)
        rgb[40:80, 55:115] = [.85, .61, .72]
        legacy = np.zeros((120, 160), np.float32)
        legacy[45:75, 60:110] = 1
        chroma, candidate, combined, added, report = chroma_probe(
            rgb, legacy, ramp=4)
        self.assertTrue(np.all(combined >= legacy))
        self.assertEqual(combined[60, 80], 1)
        self.assertGreater(candidate[42, 60], .5)
        self.assertLess(candidate[5, 5], .01)
        self.assertGreater(added[42, 60], .5)
        self.assertEqual(report['border_added_alpha_gt_005_fraction'], 0)

    def test_rejects_invalid_parameters(self):
        rgb = np.ones((60, 80, 3), np.float32)
        a = np.zeros((60, 80), np.float32)
        with self.assertRaises(ValueError):
            chroma_probe(rgb, a, paper_percentile=70)
        with self.assertRaises(ValueError):
            chroma_probe(rgb, a[:30])


if __name__ == '__main__':
    unittest.main()
