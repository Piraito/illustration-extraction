"""Regression tests for TIFF input discovery and clear empty-input errors."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import extract_illustrations as extractor


class InputDiscoveryTests(unittest.TestCase):
    def test_tif_and_tiff_are_discovered(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            incoming = base / 'input'
            incoming.mkdir()
            (incoming / 'first.tif').touch()
            (incoming / 'second.TIFF').touch()
            output = base / 'output'
            buf = io.StringIO()
            with (patch.object(sys, 'argv', [
                    'extract_illustrations.py', str(incoming), str(output)]),
                  patch.object(extractor, 'leer',
                               side_effect=RuntimeError('test-only read failure')) as reader,
                  contextlib.redirect_stdout(buf)):
                with self.assertRaises(SystemExit) as caught:
                    extractor.main()
            self.assertEqual(caught.exception.code, 1)
            self.assertEqual(reader.call_count, 2)
            self.assertIn('first.tif', buf.getvalue())
            self.assertIn('second.TIFF', buf.getvalue())

    def test_empty_selection_is_an_error_before_output_creation(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            incoming = base / 'input'
            incoming.mkdir()
            (incoming / 'not-supported.txt').touch()
            output = base / 'output'
            with (patch.object(sys, 'argv', [
                    'extract_illustrations.py', str(incoming), str(output)]),
                  contextlib.redirect_stderr(io.StringIO()) as err):
                with self.assertRaises(SystemExit) as caught:
                    extractor.main()
            self.assertEqual(caught.exception.code, 2)
            self.assertIn('No se encontraron archivos compatibles', err.getvalue())
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
