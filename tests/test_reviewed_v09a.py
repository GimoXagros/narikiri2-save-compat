import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_banked_font import collect,prepare_fonts,build
from reviewed_v09a import build as apply_review,sha

class ReviewedScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        rows,unresolved=collect(source)
        assert not unresolved
        with tempfile.TemporaryDirectory() as folder:
            chars,clear,solid,codes=prepare_fonts(rows,Path(folder)/'font')
            cls.source,_=build(source,rows,chars,clear,solid,codes)
        cls.ledger=json.loads((ROOT/'translation/v09a_reviewed_deltas.json').read_text(encoding='utf-8'))

    def test_every_reviewed_pointer_and_reproducible_target(self):
        first,report=apply_review(self.source)
        second,_=apply_review(self.source)
        self.assertEqual(first,second)
        self.assertEqual((report['reviewed'],report['bindings'],report['changed']),(8038,8946,5186))
        self.assertEqual(first[0xac3f4:0x2b2cac],self.source[0xac3f4:0x2b2cac])
        self.assertEqual(sha(first),'faa2f0ebe1f7bbd9f4a7e1d38b7d35ca2349bfed1d8c2a5d8ae45feb0f7631f6')

    def test_missing_review_and_wrong_source_fail(self):
        ledger=copy.deepcopy(self.ledger);ledger['rows'].pop()
        with self.assertRaisesRegex(ValueError,'Incomplete'):apply_review(self.source,ledger)
        with self.assertRaisesRegex(ValueError,'frozen'):apply_review(b'bad input',self.ledger)

    def test_description_overflow_is_a_build_error(self):
        ledger=copy.deepcopy(self.ledger)
        ledger['rows'][619]['spans']=[[0,0,'가'*19]]
        with self.assertRaisesRegex(ValueError,'18 x 2'):apply_review(self.source,ledger)

    def test_controls_missing_glyphs_and_numbers_fail(self):
        for bad,error in (('@P','Control'),('🙂','encode'),('９９','Number')):
            ledger=copy.deepcopy(self.ledger);ledger['rows'][0]['spans']=[[0,0,bad]]
            with self.subTest(bad=bad),self.assertRaises((ValueError,UnicodeEncodeError)):
                apply_review(self.source,ledger)

    def test_source_binding_and_overlapping_spans_fail(self):
        ledger=copy.deepcopy(self.ledger);ledger['rows'][0]['bindings']=['00000000']
        with self.assertRaisesRegex(ValueError,'Pointer changed'):apply_review(self.source,ledger)
        ledger=copy.deepcopy(self.ledger);ledger['rows'][0]['spans']=[[0,2,'가'],[1,2,'나']]
        with self.assertRaisesRegex(ValueError,'Invalid authored'):apply_review(self.source,ledger)

if __name__=='__main__':unittest.main()
