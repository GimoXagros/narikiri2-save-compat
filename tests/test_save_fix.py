from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from ips import IpsError, apply_ips, create_ips
from bps import BpsError, apply_bps, create_bps
from convert_save import (
    FORMAT_EEPROM,
    FORMAT_VBAM,
    SaveFormatError,
    convert_bytes,
    detect_format,
)
from prepare_save_test import assert_clean
from narikiri2_text_spec import decode_game_text, encode_korean_fixed_slot
from find_gba_lz77_asset import decompress_lz77_stream
from narikiri2_item_ui_font import (
    ITEM_UI_SEQUENCES,
    KNOWN_COMPACT_GLYPHS,
    compress_lz77,
)
from save_fix_spec import EXPECTED_WRITES, allowed_diff_offsets
from verify_save_fix_guard import SaveFixGuardError, verify_save_fix_bytes
from verify_inputs import gba_header_checksum


class SaveFixContractTests(unittest.TestCase):
    def test_adopted_diff_denominator_is_79(self) -> None:
        offsets = allowed_diff_offsets()
        self.assertEqual(79, len(offsets))
        self.assertEqual(len(offsets), len(set(offsets)))

    def test_each_write_has_equal_nonempty_source_and_target(self) -> None:
        for write in EXPECTED_WRITES:
            with self.subTest(write=write.write_id):
                self.assertGreater(len(write.expected_source), 0)
                self.assertEqual(len(write.expected_source), len(write.final_bytes))

    def test_ips_roundtrip_with_separate_ranges(self) -> None:
        source = bytes(range(64))
        target = bytearray(source)
        target[3:7] = b"ABCD"
        target[40:43] = b"xyz"
        patch = create_ips(source, bytes(target))
        self.assertEqual(bytes(target), apply_ips(source, patch))

    def test_ips_rejects_invalid_header_and_truncation(self) -> None:
        with self.assertRaises(IpsError):
            apply_ips(b"source", b"NOPE")
        with self.assertRaises(IpsError):
            apply_ips(b"source", b"PATCH\x00")

    def test_bps_roundtrip_and_source_guard(self) -> None:
        source = bytes(range(128))
        target = bytearray(source)
        target[3:7] = b"ABCD"
        target[110:114] = b"wxyz"
        patch = create_bps(source, bytes(target))
        self.assertEqual(bytes(target), apply_bps(source, patch))
        with self.assertRaises(BpsError):
            apply_bps(b"x" + source[1:], patch)

    def test_direct_hangul_renderer_roundtrip_is_not_the_item_ui_encoder(self) -> None:
        text = "분꽃 곡괭이 롱 보우"
        encoded = encode_korean_fixed_slot(text)
        self.assertEqual(text, decode_game_text(b"", encoded))
        self.assertEqual("8DBA89C3", encode_korean_fixed_slot("분꽃").hex().upper())
        self.assertEqual("88EC894690AA", encode_korean_fixed_slot("곡괭이").hex().upper())
        self.assertEqual("8C65208DA2906C", encode_korean_fixed_slot("롱 보우").hex().upper())

    def test_frozen_failed_poc2_sequences_remain_reproducible(self) -> None:
        self.assertEqual("4A51", ITEM_UI_SEQUENCES["분꽃"].hex().upper())
        self.assertEqual("3D", ITEM_UI_SEQUENCES["곰"].hex().upper())
        self.assertEqual("21CD5829C4", ITEM_UI_SEQUENCES["곡괭이"].hex().upper())
        self.assertEqual("5A", ITEM_UI_SEQUENCES["빵"].hex().upper())
        self.assertEqual("24D37812B2", ITEM_UI_SEQUENCES["롱보우"].hex().upper())
        for encoded in ITEM_UI_SEQUENCES.values():
            self.assertTrue(all(value == 0x12 or 0x20 <= value <= 0x7E or 0xA1 <= value <= 0xDF for value in encoded))

    def test_compact_gol_and_gong_are_not_conflated(self) -> None:
        self.assertEqual((0x94ED, "골"), KNOWN_COMPACT_GLYPHS[0x3D])
        self.assertEqual((0x94EE, "공"), KNOWN_COMPACT_GLYPHS[0x3E])

    def test_item_ui_lz77_roundtrip(self) -> None:
        source = (bytes(range(256)) * 16) + (b"KOREAN-ITEM-FONT" * 200)
        compressed = compress_lz77(source)
        decompressed = decompress_lz77_stream(compressed, 0, 0x10000)
        self.assertIsNotNone(decompressed)
        self.assertEqual(source, decompressed[0])

    def test_known_header_checksum_formula(self) -> None:
        header = bytearray(0xC0)
        header[0xA0:0xAC] = b"NARIKIRI2\0\0\0"
        header[0xAC:0xB0] = b"AN9J"
        header[0xB0:0xB2] = b"AF"
        calculated = gba_header_checksum(bytes(header))
        self.assertIsInstance(calculated, int)
        self.assertGreaterEqual(calculated, 0)
        self.assertLessEqual(calculated, 0xFF)

    def test_clean_case_rejects_save_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            (case / "candidate_a.gba").write_bytes(b"rom")
            self.assertEqual(assert_clean(case, "candidate_a"), ["candidate_a.gba"])
            (case / "candidate_a.sav").write_bytes(b"save")
            with self.assertRaises(RuntimeError):
                assert_clean(case, "candidate_a")

    def test_save_conversion_roundtrip(self) -> None:
        eeprom = b"IRIKIRAN" + bytes(range(256)) * 31 + bytes(range(248))
        self.assertEqual(8192, len(eeprom))
        vbam = convert_bytes(eeprom, FORMAT_EEPROM, FORMAT_VBAM)
        self.assertEqual(FORMAT_VBAM, detect_format(vbam))
        self.assertEqual(eeprom, convert_bytes(vbam, FORMAT_VBAM, FORMAT_EEPROM))

    def test_save_conversion_rejects_bad_size_signature_and_tail(self) -> None:
        with self.assertRaises(SaveFormatError):
            detect_format(b"\xFF" * 32768)
        with self.assertRaises(SaveFormatError):
            detect_format(b"IRIKIRAN" + b"\x00" * 8)
        eeprom = b"IRIKIRAN" + b"\x00" * (8192 - 8)
        bad_tail = eeprom + b"\xFF" * (32768 - 8192 - 1) + b"\x00"
        with self.assertRaises(SaveFormatError):
            detect_format(bad_tail)

    def test_save_fix_guard_accepts_complete_fixture_and_rejects_window_change(self) -> None:
        rom = bytearray([0xFF]) * 0xC00000
        rom[0xA0:0xAC] = b"NARIKIRI2\0\0\0"
        rom[0xAC:0xB0] = b"AN9J"
        rom[0xB0:0xB2] = b"AF"
        rom[0xBC] = 0
        for value in range(256):
            rom[0xB2] = value
            if gba_header_checksum(bytes(rom[:0xC0])) == 0x2D:
                break
        rom[0xBD] = 0x2D
        rom[0x3741D8:0x3741D8 + len(b"EEPROM_V122")] = b"EEPROM_V122"
        rom[0x3741F0:0x3741F4] = (0x2000).to_bytes(4, "little")
        rom[0x3741F4:0x3741F6] = (0x0400).to_bytes(2, "little")
        rom[0x3741F8] = 0x0E
        rom[0xA1E4:0xA1E8] = (0x089513E8).to_bytes(4,'little')
        rom[0x9513E8:0x9513F0] = b'NARIKIRI'
        for write in EXPECTED_WRITES:
            rom[write.offset:write.end] = write.final_bytes
        self.assertEqual("PASS", verify_save_fix_bytes(bytes(rom))["status"])
        rom[EXPECTED_WRITES[1].offset] ^= 0x01
        with self.assertRaises(SaveFixGuardError):
            verify_save_fix_bytes(bytes(rom))


if __name__ == "__main__":
    unittest.main()
