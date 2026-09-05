"""Decode the original OAM frame layouts to verify translated word pixels and bounds."""
import sys,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from translated_ui_graphics import battle_result_plans,battle_status_plans
from import_dalmoori_8x8 import generated_path,parse_generated_glyph

class BattleGraphicsTests(unittest.TestCase):
    def test_result_word_frames_and_preserved_numerals(self):
        source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        final=bytearray(source)
        for row in battle_result_plans(source,ROOT):
            off=row['offset'];self.assertEqual(source[off:off+len(row['payload'])],row['expected'])
            final[off:off+len(row['payload'])]=row['payload']
        # Frames5..14 are the ten shared numerals, between word frames4 and15.
        start=0x6D6C3C+44*32;end=0x6D6C3C+100*32
        self.assertEqual(final[start:end],source[start:end])
        dimensions=[[(8,8),(16,16),(32,32),(64,64)],[(16,8),(32,8),(32,16),(64,32)],[(8,16),(8,32),(16,32),(32,64)]]
        for index,word,width in [(0,'보너스',48),(1,'갈드',40),(2,'경험치',32),(3,'레벨',32),(4,'상승',24),(15,'연타',32),(16,'기술',32),(17,'상승',24)]:
            frame=struct.unpack_from('<I',source,0x3AF5C4+4+index*4)[0]-0x08000000
            count=struct.unpack_from('<I',source,frame)[0];pixels={}
            for n in range(count):
                x,y,shape,palette,tile=struct.unpack_from('<bbBBI',source,frame+4+n*8)
                w,h=dimensions[shape>>2][shape&3]
                for yy in range(h):
                    for xx in range(w):
                        off=0x6D6C3C+(tile+(yy//8)*(w//8)+xx//8)*32+(yy%8)*4+(xx%8)//2
                        pixels[(x+xx,y+yy)]=(final[off]>>(4*(xx%2)))&15
            self.assertEqual(set(pixels),{(x,y) for y in range(16) for x in range(width)})
            expected=set();x0=(width-len(word)*8)//2
            for i,ch in enumerate(word):
                _,_,_,rows=parse_generated_glyph(generated_path(ROOT/'third_party/_work/dalmoori-font',ch))
                expected.update((x0+i*8+x,4+y) for y,row in enumerate(rows) for x,c in enumerate(row) if c=='#')
            self.assertEqual({p for p,v in pixels.items() if v==15},expected,(index,word))
            self.assertTrue(set(pixels.values())<={0,2,15})

    def test_target_includes_its_fifth_tile_and_preserves_arrow(self):
        source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        rows=battle_status_plans(source,ROOT);target=next(r for r in rows if r['id']=='battle_target_graphic')
        self.assertEqual(target['offset'],0x6D63BC)
        self.assertEqual(len(target['payload']),5*32)
        self.assertEqual(target['offset']+len(target['payload']),0x6D645C)

if __name__=='__main__':unittest.main()
