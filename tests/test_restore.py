"""Only synthetic data; no ROM, extracted instructions, or save fixtures."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import restore as r


def fixture():
    source = bytes(range(32))
    donor = bytes((i + 101) % 256 for i in range(32))
    target = source[:4] + donor[4:7] + source[7:20] + donor[20:22] + source[22:]
    recipe = r.Recipe(r.Image(32, r.digest(source)), r.Image(32, r.digest(donor)),
                      r.Image(32, r.digest(target)), ((4, 3), (20, 2)), ((4, 7), (20, 22)))
    return source, donor, target, recipe


class RestorationTests(unittest.TestCase):
    def setUp(self):
        self.source, self.donor, self.target, self.recipe = fixture()

    def test_restores_only_registered_windows(self):
        self.assertEqual(r.restore_bytes(self.source, self.donor, self.recipe), self.target)
        self.assertEqual(self.source, bytes(range(32)))

    def test_two_builds_identical(self):
        self.assertEqual(r.restore_bytes(self.source, self.donor, self.recipe),
                         r.restore_bytes(self.source, self.donor, self.recipe))

    def test_wrong_same_size_source_rejected(self):
        with self.assertRaises(r.RestoreError):
            r.restore_bytes(bytes(32), self.donor, self.recipe)

    def test_wrong_same_size_donor_rejected(self):
        with self.assertRaises(r.RestoreError):
            r.restore_bytes(self.source, bytes(32), self.recipe)

    def test_truncated_or_extended_inputs_rejected(self):
        for source, donor in ((self.source[:-1], self.donor), (self.source + b'0', self.donor),
                              (self.source, self.donor[:-1]), (self.source, self.donor + b'0')):
            with self.subTest(source_size=len(source), donor_size=len(donor)):
                with self.assertRaises(r.RestoreError):
                    r.restore_bytes(source, donor, self.recipe)

    def test_expected_result_hash_enforced(self):
        recipe = replace(self.recipe, result=r.Image(32, '0' * 64))
        with self.assertRaises(r.RestoreError):
            r.restore_bytes(self.source, self.donor, recipe)

    def test_modified_byte_outside_allowlist_rejected_even_with_matching_hash(self):
        bad = bytes([self.target[0] ^ 1]) + self.target[1:]
        recipe = replace(self.recipe, result=r.Image(32, r.digest(bad)))
        with self.assertRaises(r.RestoreError):
            r.verify_result(self.source, self.donor, bad, recipe)

    def test_restored_window_must_match_donor(self):
        bad = self.target[:4] + bytes([self.target[4] ^ 1]) + self.target[5:]
        recipe = replace(self.recipe, result=r.Image(32, r.digest(bad)))
        with self.assertRaises(r.RestoreError):
            r.verify_result(self.source, self.donor, bad, recipe)

    def test_growth_rejected(self):
        with self.assertRaises(r.RestoreError):
            r.validate_recipe(replace(self.recipe, result=r.Image(33, '0' * 64)))

    def test_overlapping_or_unordered_windows_rejected(self):
        for windows in (((4, 5), (7, 3)), ((20, 2), (4, 3))):
            with self.subTest(windows=windows), self.assertRaises(r.RestoreError):
                r.validate_recipe(replace(self.recipe, windows=windows))

    def test_invalid_window_bounds_rejected(self):
        for windows in (((-1, 3),), ((4, 0),), ((31, 2),), ((4.0, 3),)):
            with self.subTest(windows=windows), self.assertRaises(r.RestoreError):
                r.validate_recipe(replace(self.recipe, windows=windows))

    def test_invalid_difference_intervals_rejected(self):
        for ranges in ((), ((4, 8),), ((4, 6), (5, 7)), ((5, 5),), ((20, 22), (4, 7))):
            with self.subTest(ranges=ranges), self.assertRaises(r.RestoreError):
                r.validate_recipe(replace(self.recipe, differences=ranges))

    def test_unchanged_donor_bytes_can_exist_inside_write_window(self):
        donor = self.donor[:5] + self.source[5:6] + self.donor[6:]
        target = self.target[:5] + self.source[5:6] + self.target[6:]
        recipe = replace(self.recipe, japanese=r.Image(32, r.digest(donor)),
                         result=r.Image(32, r.digest(target)), differences=((4, 5), (6, 7), (20, 22)))
        self.assertEqual(r.restore_bytes(self.source, donor, recipe), target)


class FileSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='an9j-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.donor, self.target, self.recipe = fixture()
        self.k = self.root / 'k.gba'
        self.j = self.root / 'j.gba'
        self.out = self.root / 'new.gba'
        self.k.write_bytes(self.source)
        self.j.write_bytes(self.donor)

    def run_restore(self, out=None):
        return r.restore_files(self.k, self.j, out or self.out, self.recipe)

    def test_new_output_preserves_inputs_and_save(self):
        save = self.root / 'new.sav'
        save.write_bytes(b'synthetic-save-sentinel')
        report = self.run_restore()
        self.assertEqual(self.out.read_bytes(), self.target)
        self.assertEqual(self.k.read_bytes(), self.source)
        self.assertEqual(self.j.read_bytes(), self.donor)
        self.assertEqual(save.read_bytes(), b'synthetic-save-sentinel')
        self.assertEqual(report['changed_bytes'], 5)

    def test_existing_output_preserved(self):
        self.out.write_bytes(b'existing')
        with self.assertRaises(r.RestoreError):
            self.run_restore()
        self.assertEqual(self.out.read_bytes(), b'existing')

    def test_both_input_paths_protected(self):
        for destination in (self.k, self.j):
            with self.subTest(destination=destination), self.assertRaises(r.RestoreError):
                self.run_restore(destination)
        self.assertEqual(self.k.read_bytes(), self.source)
        self.assertEqual(self.j.read_bytes(), self.donor)

    def test_save_output_extension_rejected(self):
        with self.assertRaises(r.RestoreError):
            self.run_restore(self.root / 'new.sav')
        self.assertFalse((self.root / 'new.sav').exists())

    def test_invalid_input_creates_no_output(self):
        self.k.write_bytes(bytes(32))
        with self.assertRaises(r.RestoreError):
            self.run_restore()
        self.assertFalse(self.out.exists())

    def test_missing_donor_creates_no_output(self):
        self.j.unlink()
        with self.assertRaises(r.RestoreError):
            self.run_restore()
        self.assertFalse(self.out.exists())

    def test_missing_output_parent_creates_nothing(self):
        missing = self.root / 'missing' / 'new.gba'
        with self.assertRaises(r.RestoreError):
            self.run_restore(missing)
        self.assertFalse(missing.parent.exists())

    def test_late_output_creation_does_not_overwrite(self):
        original = r.restore_bytes
        def racing_build(*args):
            result = original(*args)
            self.out.write_bytes(b'created-by-someone-else')
            return result
        with patch.object(r, 'restore_bytes', side_effect=racing_build):
            with self.assertRaises(r.RestoreError):
                self.run_restore()
        self.assertEqual(self.out.read_bytes(), b'created-by-someone-else')

    def test_cli_rejects_unsupported_fixture_without_force_option(self):
        with patch('sys.stderr'):
            self.assertEqual(r.main(['--korean', str(self.k), '--japanese', str(self.j),
                                     '--output', str(self.out)]), 1)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
