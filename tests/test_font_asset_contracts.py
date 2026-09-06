"""Preserved source, palette and real-ROM font compression contracts."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_dalmoori_gba_font import pack_4bpp, place, unpack_4bpp
from import_dalmoori_8x8 import PINNED_COMMIT
from find_gba_lz77_asset import decompress_lz77_stream
from narikiri2_item_ui_font import compress_lz77

class DalmooriAssetTests(unittest.TestCase):
    def test_source_manifest_is_pinned(self):
        data = json.loads((ROOT / "third_party/dalmoori-font/SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(data["source_commit"], PINNED_COMMIT)
        self.assertEqual(data["license"], "Apache-2.0")

    def test_4bpp_nibble_and_row_orientation_golden(self):
        bitmap = [[0] * 8 for _ in range(8)]
        bitmap[0][0] = bitmap[7][7] = 1
        tile = pack_4bpp(bitmap, 0, 15)
        self.assertEqual(tile[0], 0x0F)
        self.assertEqual(tile[-1], 0xF0)
        self.assertEqual(unpack_4bpp(tile, 0, 15), bitmap)

    def test_halfwidth_placement_keeps_fixed_cell(self):
        bitmap = [[1, 0, 0, 1] for _ in range(8)]
        placed = place(bitmap, x_offset=0)
        self.assertEqual(placed[0], [1, 0, 0, 1, 0, 0, 0, 0])

    def test_palette_indices_are_strict(self):
        bitmap = [[0] * 8 for _ in range(8)]
        with self.assertRaises(ValueError):
            pack_4bpp(bitmap, 15, 15)

    def test_original_font_noop_is_lossless_and_deterministic(self):
        rom = (ROOT / "output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba").read_bytes()
        raw, _ = decompress_lz77_stream(rom, 0xCA3F4, 0x10000)
        first = compress_lz77(raw)
        second = compress_lz77(raw)
        self.assertEqual(first, second)
        self.assertEqual(decompress_lz77_stream(first, 0, 0x10000)[0], raw)
        self.assertLessEqual(len(first), 0xCABC4 - 0xCA3F4)

    def test_reexamined_compact_codes_are_not_conflated(self):
        # The supplied instruction's 94ED=곰 premise is contradicted by ROM
        # glyph evidence and real item-name use. Preserve the verified result.
        from item_name_consumer import decode_verified_compact
        self.assertEqual(decode_verified_compact(bytes.fromhex("94ED")), "골")
        self.assertEqual(decode_verified_compact(bytes.fromhex("94EE")), "공")
