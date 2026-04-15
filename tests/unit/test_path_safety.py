import tempfile
import unittest
from pathlib import Path

from shared.infrastructure.path_safety import UnsafePathError, resolve_safe_path


class ResolveSafePathTests(unittest.TestCase):
    def test_relative_path_stays_under_base_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resolved = resolve_safe_path('nested/file.csv', base_root=tmpdir, allowed_roots=[tmpdir])
            self.assertEqual(resolved, Path(tmpdir).resolve() / 'nested/file.csv')

    def test_absolute_path_within_root_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_file = Path(tmpdir) / 'safe.csv'
            resolved = resolve_safe_path(str(safe_file), base_root=tmpdir, allowed_roots=[tmpdir])
            self.assertEqual(resolved, safe_file.resolve(strict=False))

    def test_absolute_path_outside_root_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(UnsafePathError):
                resolve_safe_path('/etc/passwd', base_root=tmpdir, allowed_roots=[tmpdir])

    def test_relative_traversal_outside_root_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(UnsafePathError):
                resolve_safe_path('../../etc/passwd', base_root=tmpdir, allowed_roots=[tmpdir])

    def test_data_prefix_traversal_is_blocked(self):
        with self.assertRaises(UnsafePathError):
            resolve_safe_path('/data/../../etc/passwd', base_root='/data', allowed_roots=['/data/sample_data', '/data/projects'])


if __name__ == '__main__':
    unittest.main()
