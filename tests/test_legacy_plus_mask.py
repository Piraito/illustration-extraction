"""Checks for diagnostic-only alpha additions (never modifications to legacy)."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from legacy_plus_mask import propose_legacy_plus


class LegacyPlusTests(unittest.TestCase):
    def test_only_adds_where_local_chroma_supports_it(self):
        rgb = np.full((200, 260, 3), [.96, .95, .92], np.float32)
        legacy = np.zeros((200, 260), np.float32)
        legacy[80:125, 100:160] = .85
        rgb[70:133, 90:170] = [.92, .78, .84]  # adjacent rose wash
        rgb[12:30, 12:30] = [.72, .26, .24]  # isolated scan mark
        proposed, added = propose_legacy_plus(rgb, legacy)
        self.assertTrue(np.all(proposed >= legacy - 1e-6))
        self.assertGreater(proposed[78, 130], legacy[78, 130])
        self.assertEqual(float(proposed[18, 18]), 0)
        self.assertEqual(float(proposed[160, 190]), 0)
        self.assertTrue(np.allclose(proposed - legacy, added))

    def test_uncolored_paper_remains_empty(self):
        rgb = np.full((120, 150, 3), [.96, .95, .92], np.float32)
        legacy = np.zeros((120, 150), np.float32)
        legacy[30:70, 50:100] = 1
        proposed, added = propose_legacy_plus(rgb, legacy)
        np.testing.assert_array_equal(proposed, legacy)
        self.assertEqual(float(added.max()), 0)

    def test_bad_shapes_fail(self):
        with self.assertRaises(ValueError):
            propose_legacy_plus(np.ones((5, 5, 3), np.float32),
                                np.zeros((4, 5), np.float32))


if __name__ == '__main__':
    unittest.main()
