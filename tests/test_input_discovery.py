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

    def test_single_tiff_file_is_processed_with_its_original_stem(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            incoming = base / '46-34.tif'
            incoming.touch()
            output = base / 'results'
            with (patch.object(sys, 'argv', [
                    'extract_illustrations.py', str(incoming), str(output),
                    '--mask-method', 'acuarela', '--output-format', 'tiff-alpha']),
                  patch.object(extractor, 'leer',
                               side_effect=RuntimeError('single file recognized')) as reader,
                  contextlib.redirect_stdout(io.StringIO()) as out):
                with self.assertRaises(SystemExit) as caught:
                    extractor.main()
            self.assertEqual(caught.exception.code, 1)
            reader.assert_called_once()
            self.assertEqual(reader.call_args.args[0], incoming)
            self.assertIn('[1/1] ERROR 46-34.tif', out.getvalue())
            self.assertTrue(output.exists())

    def test_single_file_with_unsupported_extension_fails(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            incoming = base / 'notes.txt'
            incoming.touch()
            output = base / 'results'
            with (patch.object(sys, 'argv', [
                    'extract_illustrations.py', str(incoming), str(output)]),
                  contextlib.redirect_stderr(io.StringIO()) as err):
                with self.assertRaises(SystemExit) as caught:
                    extractor.main()
            self.assertEqual(caught.exception.code, 2)
            self.assertIn('Extensión de archivo no compatible', err.getvalue())
            self.assertFalse(output.exists())

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
