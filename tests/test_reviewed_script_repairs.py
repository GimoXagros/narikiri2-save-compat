"""Regress the actual malformed controls and untranslated fields found in FFR."""
import collections,hashlib,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from repair_reviewed_script_records import plans
from narikiri2_text_spec import JAPANESE_SHA256,decode_game_text

class ReviewedScriptRepairs(unittest.TestCase):
    def test_repaired_controls_match_independent_japanese_source(self):
        source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        jp=next(x.read_bytes() for x in ROOT.glob('*.gba') if x.stat().st_size==0x800000 and hashlib.sha256(x.read_bytes()).hexdigest()==JAPANESE_SHA256)
        decisions=json.loads((ROOT/'translation/reviewed_script_repairs.json').read_text(encoding='utf-8'))
        repairs=plans(source,ROOT)
        self.assertEqual(len(repairs),23)
        for decision,repair in zip(decisions,repairs):
            start=int(decision['japanese_target'],16)
            original=jp[start:jp.index(b'\0',start)].decode('cp932')
            actual=decode_game_text(source,repair['payload'])
            with self.subTest(storage=decision['storage']):
                for pattern in (r'@[A-Za-z]',r'%[0-9]*[A-Za-z]'):
                    self.assertEqual(collections.Counter(re.findall(pattern,actual)),collections.Counter(re.findall(pattern,original)))
                self.assertNotRegex(actual,'[ぁ-ゖァ-ヺ一-鿿ｦ-ﾟ]')

if __name__=='__main__':unittest.main()
