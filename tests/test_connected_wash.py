"""Regression tests for diagnostic connected-color wash recovery."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from connected_wash import connected_wash


class ConnectedWashTests(unittest.TestCase):
    def test_connected_wash_can_grow_beyond_legacy_without_erasing(self):
        rgb = np.full((160, 220, 3), [.96, .95, .92], np.float32)
        legacy = np.zeros((160, 220), np.float32)
        rgb[55:100, 50:150] = [.88, .73, .80]
        legacy[68:88, 70:110] = 1.
        proposed, addition, details = connected_wash(rgb, legacy)
        self.assertTrue(np.all(proposed >= legacy))
        self.assertGreater(proposed[60, 55], .05)
        self.assertEqual(float(proposed[15, 15]), 0.)
        self.assertGreater(details['new_pixels_alpha_gt_005'], 0)
        np.testing.assert_allclose(addition, proposed - legacy)

    def test_unconnected_spot_not_recovered(self):
        rgb = np.full((160, 220, 3), [.96, .95, .92], np.float32)
        legacy = np.zeros((160, 220), np.float32)
        rgb[55:100, 50:150] = [.88, .73, .80]
        legacy[68:88, 70:110] = 1.
        rgb[10:20, 10:20] = [.7, .4, .6]
        proposed, _, _ = connected_wash(rgb, legacy)
        self.assertEqual(float(proposed[15, 15]), 0.)

    def test_paper_must_not_gain_alpha(self):
        rgb = np.full((90, 120, 3), [.96, .95, .92], np.float32)
        legacy = np.zeros((90, 120), np.float32)
        legacy[30:70, 40:80] = .85
        proposed, addition, _ = connected_wash(rgb, legacy)
        np.testing.assert_array_equal(proposed, legacy)
        self.assertEqual(float(addition.max()), 0.)

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            connected_wash(np.zeros((30, 30, 3), np.float32),
                           np.zeros((30, 31), np.float32))


if __name__ == '__main__':
    unittest.main()
