import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from transcribe_compact_font import transcribe, READINGS


class CompactTranscriptionTests(unittest.TestCase):
    def test_gol_gong_and_b1_do_not_use_historical_misreadings(self):
        self.assertEqual(transcribe(b"=")["text"], "골")
        self.assertEqual(transcribe(b">")["text"], "공")
        self.assertEqual(transcribe(bytes.fromhex("12A112"))["text"], "블")
        self.assertEqual(transcribe(bytes.fromhex("29BB12BE"))["text"], "없음")

    def test_initial_and_vowel_final_pieces_compose_in_order(self):
        self.assertEqual(transcribe(bytes.fromhex("29B112A712207E24CF29C468"))["text"], "어스 브레이드")
        self.assertEqual(transcribe(bytes.fromhex("12CB1224CF12A7"))["text"], "크레스")

    def test_formatter_toggle_and_raw_toggle_have_same_glyph_effect(self):
        a = transcribe(b"%h\xa1%h\x24\xcf")
        b = transcribe(bytes.fromhex("12A11224CF"))
        self.assertEqual(a["text"], b["text"])
        self.assertNotEqual(a["units"], b["units"])
        self.assertEqual(bytes.fromhex("".join(u["raw_hex"] for u in a["units"])), b"%h\xa1%h\x24\xcf")

    def test_format_arguments_and_newlines_remain_explicit(self):
        result = transcribe(b"%l%3d:%02d\n%s")
        for token in ("⟦%l⟧", "⟦%3d⟧", "⟦%02d⟧", "\n", "⟦%s⟧"):
            self.assertIn(token, result["text"])
        self.assertEqual(bytes.fromhex("".join(u["raw_hex"] for u in result["units"])), b"%l%3d:%02d\n%s")

    def test_mark_and_private_control_bytes_are_never_silently_dropped(self):
        for raw in (b"\xde", b"\xdf", b"\x7f", b"\0"):
            result = transcribe(raw)
            self.assertTrue(result["unsupported"])
            self.assertIn("RAW:", result["text"])
        self.assertEqual(len(READINGS), 217)


if __name__ == "__main__":
    unittest.main()
