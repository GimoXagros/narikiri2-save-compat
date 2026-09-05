from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from item_name_consumer import decode_verified_compact, encode_verified_compact, tiles_for_name, name_advance_px


class ItemConsumerRegressionTests(unittest.TestCase):
    def test_gol_gong_decode_matches_reexamined_glyphs(self):
        self.assertEqual("골", decode_verified_compact(bytes.fromhex("94ED")))
        self.assertEqual("공", decode_verified_compact(bytes.fromhex("94EE")))

    def test_gol_gong_encode_roundtrip(self):
        for text, raw in (("골", "94ED"), ("공", "94EE")):
            self.assertEqual(raw, encode_verified_compact(text).hex().upper())
            self.assertEqual(text, decode_verified_compact(encode_verified_compact(text)))

    def test_gom_cannot_silently_reuse_gol(self):
        with self.assertRaises(ValueError):
            encode_verified_compact("곰")

    def test_unknown_and_truncated_compact_code_rejected(self):
        for raw in (b"", b"\x94", bytes.fromhex("94ED94EE"), bytes.fromhex("94EF")):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_verified_compact(raw)

    def test_mode_toggle_selects_upper_tile_bank(self):
        self.assertEqual([0x77, 0xB7, 0x77], tiles_for_name(bytes.fromhex("A712A712A7")))

    def test_ascii_is_independent_of_kana_mode(self):
        self.assertEqual([0x2D, 0x2D], tiles_for_name(bytes.fromhex("3D123D")))

    def test_mode_toggle_is_zero_width_and_has_local_lifetime(self):
        self.assertEqual(0, name_advance_px(b"\x12"))
        self.assertEqual([0xB7], tiles_for_name(bytes.fromhex("12A7")))
        self.assertEqual([0x77], tiles_for_name(bytes.fromhex("A7")))

    def test_black_belt_mode_is_preserved(self):
        self.assertEqual([0x11, 0x86, 0xCC, 0x2A, 0x81, 0x14, 0x94, 0x13, 0x94], tiles_for_name(bytes.fromhex("21B612BC123AB124C423C4")))

    def test_bow_mode_changes_only_u_tile(self):
        self.assertEqual([0x14,0xA3,0x68,0xC2], tiles_for_name(bytes.fromhex("24D37812B2")))

    def test_direct_hangul_is_not_a_valid_compact_name(self):
        with self.assertRaises(ValueError):
            tiles_for_name(bytes.fromhex("88EC894690AA"))

    def test_nul_and_unknown_controls_are_not_silently_skipped(self):
        for raw in (b"A\0B", b"\x13\x02", b"\x0A", b"\xDE", b"\xDF"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                tiles_for_name(raw)

    def test_space_is_a_consumed_tile_not_padding(self):
        self.assertEqual([0x31,0x10,0x32], tiles_for_name(b"A B"))
        self.assertEqual(24, name_advance_px(b"A B"))


if __name__ == "__main__":
    unittest.main()
