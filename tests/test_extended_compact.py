"""Checks the newly reconstructed table bounds and real ARM accessor behavior."""
import csv
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_extended_compact import audit_accessors, source_name_equivalent
from extended_compact_spec import TABLES, extended_fields, validate_tables
from build_compact_target_catalog import known_compact_storages


class ExtendedCompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba").read_bytes()

    def test_ordinary_battle_name_57_and_monster_163_are_included(self):
        fields = extended_fields()
        self.assertEqual(fields[0x375E24], ("BATTLE_NAME_057", "BATTLE_NAME"))
        self.assertEqual(fields[0x3AE694], ("SELECT_MONSTER_163", "SELECT_MONSTER"))
        self.assertEqual(len(fields), 704)
        self.assertFalse(set(fields) & set(known_compact_storages()))

    def test_null_list_terminators_are_required(self):
        validate_tables(self.source)
        for table in TABLES:
            if table.identity.startswith("SELECT_") or table.identity == "BATTLE_COMMAND":
                changed = bytearray(self.source)
                struct.pack_into("<I", changed, table.end, 0x08950000)
                with self.assertRaisesRegex(ValueError, "terminator"):
                    validate_tables(changed)

    def test_invalid_pointer_and_missing_terminator_are_rejected(self):
        changed = bytearray(self.source)
        struct.pack_into("<I", changed, 0x374A38, 0x07000000)
        with self.assertRaisesRegex(ValueError, "outside ROM"):
            validate_tables(changed)
        changed = bytearray(self.source)
        struct.pack_into("<I", changed, 0x374A38, 0x08BFFFFF)
        changed[-1] = 65
        with self.assertRaisesRegex(ValueError, "unterminated"):
            validate_tables(changed)

    def test_all_accessor_indices_and_selector_paths(self):
        self.assertEqual(audit_accessors(self.source)["total"], 544)

    def test_source_comparison_preserves_aliases_and_spaces(self):
        self.assertTrue(source_name_equivalent("ｱｰｽｸｴｲｸ", "アースクエイク"))
        self.assertTrue(source_name_equivalent("%hｶﾞｰﾄﾞ", "ガード"))
        self.assertFalse(source_name_equivalent("ﾄﾞﾙｲﾄﾞ", "ドルイドマスター"))
        self.assertFalse(source_name_equivalent("ｱｲｽ ﾌｫｰﾙ", "アイスフォール"))
        self.assertFalse(source_name_equivalent("%s", ""))


if __name__ == "__main__":
    unittest.main()
