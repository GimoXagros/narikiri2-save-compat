"""Reject public artifacts hidden behind innocent names and external dependencies."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_repository import inspect_content


class RepositoryIntegrationTests(unittest.TestCase):
    def test_archives_and_patch_bytes_cannot_hide_as_documentation(self):
        for raw in (b'PK\x03\x04payload', b'BPS1payload', b'PATCHpayload', b'plain\0data'):
            with self.assertRaises(ValueError):
                inspect_content('notes.md', raw)

    def test_game_and_save_extensions_are_excluded(self):
        for name in ('fixture.gba', 'sample.sav', 'tool.dll', 'old.bps'):
            with self.assertRaises(ValueError):
                inspect_content(name, b'not a binary signature')

    def test_historical_reference_is_allowed_only_outside_active_code(self):
        reference = ('https://github.com/GimoXagros/narikiri2-' + 'an9j-save-fix').encode()
        inspect_content('MIGRATION.md', reference)
        with self.assertRaises(ValueError):
            inspect_content('tools/build.py', reference)

    def test_logo_exception_requires_original_bytes(self):
        with self.assertRaises(ValueError):
            inspect_content('logo.png', b'changed image')
