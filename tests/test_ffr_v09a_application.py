"""Protect real release input identities and existing user output files."""
import hashlib, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from apply_ffr_v09a import checked, NAME, SOURCE, TARGET
from bps import create_bps

class FfrV09aApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = next(p.read_bytes() for p in ROOT.glob('*.gba') if p.stat().st_size == 12582912 and hashlib.sha256(p.read_bytes()).hexdigest() == SOURCE)
        from reviewed_v09a import build
        cls.target,_ = build((ROOT/'output/v0.9-final-build/NARIKIRI2_AN9J_K_DALMOORI_v0.9.gba').read_bytes())
        cls.patch = create_bps(cls.source, cls.target)

    def test_real_patch_reproduces_frozen_target(self):
        actual = checked(self.source, self.patch)
        self.assertEqual(actual, self.target)
        self.assertEqual(hashlib.sha256(actual).hexdigest(), TARGET)

    def test_wrong_size_source_rejected(self):
        with self.assertRaises(ValueError): checked(self.source[:0x800000], self.patch)

    def test_one_byte_source_change_rejected(self):
        changed = bytearray(self.source); changed[-1] ^= 1
        with self.assertRaises(ValueError): checked(bytes(changed), self.patch)

    def test_tampered_patch_rejected(self):
        changed = bytearray(self.patch); changed[-1] ^= 1
        with self.assertRaises(ValueError): checked(self.source, bytes(changed))

    def test_existing_output_preserved_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'existing.gba'; output.write_bytes(b'user data')
            r = subprocess.run([sys.executable, str(ROOT/'tools/apply_ffr_v09a.py'), str(Path(d)/'absent.gba'), '--output', str(output)], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(b'Output exists', r.stderr)
            self.assertEqual(output.read_bytes(), b'user data')

if __name__ == '__main__': unittest.main()
