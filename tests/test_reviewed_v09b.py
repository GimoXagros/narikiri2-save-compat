"""Real-source guards, final patch identity and pointer-table consumer regression."""
import copy
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import reviewed_v09b as review
from apply_ffr_v09b import checked, TARGET
from bps import create_bps
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR


class Beta3ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT/'output/v0.9b-final-build/review_intermediate.gba').read_bytes()
        cls.jp = next(p.read_bytes() for p in ROOT.glob('*.gba') if p.stat().st_size == 0x800000)
        cls.beta3 = next(p.read_bytes() for p in ROOT.glob('*.gba') if p.stat().st_size == 0x980000)
        cls.target, cls.report = review.build(cls.source, cls.jp)
        cls.patch = create_bps(cls.beta3, cls.target)

    def test_exact_target_and_protected_assets(self):
        self.assertEqual(hashlib.sha256(self.target).hexdigest(), TARGET)
        self.assertEqual(review.build(self.source, self.jp)[0], self.target)
        for a, b in ((0xA601C, 0xA6800), (0xAC3F4, 0x2B2CAC)):
            self.assertEqual(self.target[a:b], self.beta3[a:b])
        self.assertEqual((self.report['corrected'], self.report['compact_corrected']), (285, 16))

    def test_wrong_inputs_and_reapplication_rejected(self):
        self.assertEqual(checked(self.beta3, self.patch), self.target)
        for wrong in (self.jp, self.source, self.target, self.beta3[:-1], b''):
            with self.subTest(size=len(wrong)), self.assertRaises(ValueError):
                checked(wrong, self.patch)
        damaged = bytearray(self.patch); damaged[-1] ^= 1
        with self.assertRaises(ValueError): checked(self.beta3, damaged)
        with self.assertRaises(ValueError): review.build(self.beta3, self.jp)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'keep.gba'; out.write_bytes(b'personal data')
            result = subprocess.run([sys.executable, str(ROOT/'tools/apply_ffr_v09b.py'),
                                     str(Path(folder)/'absent.gba'), '--output', str(out)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(out.read_bytes(), b'personal data')

    def test_bound_ledger_failures(self):
        original = json.loads((ROOT/'translation/v09b_japanese_review.json').read_text(encoding='utf-8'))
        changes = [('bindings', []), ('review', 'PENDING'), ('final', original[0]['final']+'@P'),
                   ('final', original[0]['final']+'９９'), ('japanese_sha256', '0'*64),
                   ('source_sha256', '0'*64), ('bindings', ['000AC3F4']),
                   ('japanese_binding', '00000000')]
        real_loads = json.loads
        for key, value in changes:
            ledger = copy.deepcopy(original); ledger[0][key] = value
            def substituted(data, *args, **kwargs):
                parsed = real_loads(data, *args, **kwargs)
                return ledger if parsed == original else parsed
            with self.subTest(key=key, value=value), patch.object(review.json, 'loads', substituted):
                with self.assertRaises(ValueError): review.build(self.source, self.jp)

    def test_trade_consumer_loads_two_valid_strings(self):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        cpu.mem_map(0x08000000, 0x1000000); cpu.mem_write(0x08000000, self.target)
        cpu.mem_map(0x03000000, 0x8000)
        cpu.reg_write(UC_ARM_REG_SP, 0x03007E00); cpu.reg_write(UC_ARM_REG_LR, 0x02000001)
        cpu.emu_start(0x080A48C1, 0x080A48D0, count=32)
        loaded = bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_SP), 8))
        self.assertEqual(loaded, self.target[0x373760:0x373768])
        for pointer in struct.unpack('<II', loaded):
            self.assertTrue(0x08000000 <= pointer < 0x08000000+len(self.target))
            self.assertEqual(self.target[pointer-0x08000000:pointer-0x08000000+2], b'%l')


if __name__ == '__main__': unittest.main()
