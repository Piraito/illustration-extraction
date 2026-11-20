"""Diagnostic script contract tests without any original scan files."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from diagnose_masks import diagnostics, parse_region


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.rgb = np.full((80, 100, 3), [.95, .93, .90], np.float32)
        self.legacy = np.zeros((80, 100), np.float32)
        self.adaptive = np.zeros((80, 100), np.float32)
        self.legacy[20:40, 20:40] = .9
        self.adaptive[20:40, 20:40] = .2
        self.adaptive[50:60, 50:60] = .8

    def test_differences_and_region_statistics(self):
        with (patch('diagnose_masks.extraer',
                    return_value=(self.rgb, self.legacy)),
              patch('diagnose_masks.adaptive_alpha',
                    return_value=self.adaptive)):
            images, report = diagnostics(self.rgb, [
                ('aguada', 20, 20, 20, 20)])
        difference = images['diferencia_rojo_legacy_azul_adaptive.png']
        self.assertEqual(difference.shape, (80, 100, 3))
        self.assertGreater(int(difference[30, 30, 0]), 150)
        self.assertEqual(int(difference[30, 30, 2]), 0)
        self.assertGreater(int(difference[55, 55, 2]), 150)
        self.assertEqual(int(difference[55, 55, 0]), 0)
        self.assertEqual(report['regions']['aguada']['pixels'], 400)
        self.assertGreater(
            report['regions']['aguada']['legacy_minus_adaptive_mean'], .6)
        self.assertEqual(images['original_srgb.png'].shape, (80, 100, 3))

    def test_invalid_region_rejected(self):
        with (patch('diagnose_masks.extraer',
                    return_value=(self.rgb, self.legacy)),
              patch('diagnose_masks.adaptive_alpha',
                    return_value=self.adaptive)):
            with self.assertRaises(ValueError):
                diagnostics(self.rgb, [('fuera', 90, 50, 30, 40)])

    def test_parse_region(self):
        self.assertEqual(parse_region('aguada:10:20:30:40'),
                         ('aguada', 10, 20, 30, 40))


if __name__ == '__main__':
    unittest.main()
