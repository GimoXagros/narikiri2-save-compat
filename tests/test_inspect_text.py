"""Execute the inspection consumer with real ROM tables and pinned font pixels."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_banked_font import collect,prepare_fonts,build,encode,token
from inspect_text_fix import apply,plans
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB
from unicorn.arm_const import *


class InspectTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        cls.rows,_=collect(source)
        cls.temp=tempfile.TemporaryDirectory()
        cls.chars,cls.clear,solid,codes=prepare_fonts(cls.rows,Path(cls.temp.name)/'font')
        cls.baseline,_=build(source,cls.rows,cls.chars,cls.clear,solid,codes)
        cls.target,cls.writes=apply(cls.baseline)
        cls.index={c:i for i,c in enumerate(cls.chars)}

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def cpu(self):
        c=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
        for base,size in ((0x08000000,0x1000000),(0x02000000,0x40000),
                          (0x03000000,0x8000),(0x06000000,0x20000)):
            c.mem_map(base,size)
        c.mem_write(0x08000000,self.target)
        c.mem_write(0x02000f18,struct.pack('<I',0x08721d38))
        c.mem_write(0x02000f24,struct.pack('<I',0x02010000))
        return c

    def render(self,c,raw,x,y):
        c.mem_write(0x02010000,b'\xd5'*0x800)
        c.mem_write(0x06000000,b'\xa6'*0x20000)
        c.mem_write(0x02002000,raw+b'\0')
        c.reg_write(UC_ARM_REG_CPSR,0x3f)
        c.reg_write(UC_ARM_REG_SP,0x03007e00)
        c.reg_write(UC_ARM_REG_LR,0x02020001)
        c.reg_write(UC_ARM_REG_R0,x);c.reg_write(UC_ARM_REG_R1,y)
        c.reg_write(UC_ARM_REG_R2,0x02002000)
        saved=(UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8)
        for i,reg in enumerate(saved):c.reg_write(reg,0x11110000+i)
        c.emu_start(0x08025fdd,0x02020000,count=100000)
        self.assertEqual(c.reg_read(UC_ARM_REG_PC),0x02020000)
        self.assertEqual(c.reg_read(UC_ARM_REG_SP),0x03007e00)
        for i,reg in enumerate(saved):self.assertEqual(c.reg_read(reg),0x11110000+i)

    def test_every_monster_and_label_pixels_and_write_ownership(self):
        c=self.cpu()
        cases=[(r['text'],1,0) for r in self.rows if r['category']=='MONSTER']
        cases += [('공격:',1,3),('강함:',1,5),('약함:',1,7)]
        for text,x,y in cases:
            with self.subTest(text=text):
                self.assertLessEqual(x+len(text),16)
                self.render(c,encode(text,self.index),x,y)
                expected_vram=bytearray(b'\xa6'*0x20000)
                expected_map=bytearray(b'\xd5'*0x800)
                for n,char in enumerate(text):
                    if char in self.index:
                        tile=72+(y//2)*16+x+n
                        self.assertTrue(72<=tile<=135)
                        raw=self.clear[self.index[char]*32:(self.index[char]+1)*32]
                        pixels=bytes(175 if value else 161 for byte in raw for value in (byte&15,byte>>4))
                        expected_vram[0x8000+tile*64:0x8040+tile*64]=pixels
                    else:
                        offset=struct.unpack_from('<h',self.baseline,0x3afb82+ord(char)*2)[0]
                        tile=self.baseline[0x721d38+offset]
                    expected_map[y*16+x+n]=tile
                self.assertEqual(bytes(c.mem_read(0x06000000,0x20000)),expected_vram)
                self.assertEqual(bytes(c.mem_read(0x02010000,0x800)),expected_map)

    def test_hp_digits_and_all_eight_element_icons_remain_original(self):
        c=self.cpu()
        for raw,x,y in ((b'HP  139/  320',1,1),(bytes(range(0x80,0x88)),7,3),
                        (bytes(range(0x80,0x88)),5,5),(bytes(range(0x80,0x88)),5,7)):
            self.render(c,raw,x,y)
            expected=bytes(self.baseline[0x721d38+struct.unpack_from('<h',self.baseline,0x3afb82+code*2)[0]] for code in raw)
            self.assertEqual(bytes(c.mem_read(0x02010000+y*16+x,len(raw))),expected)
            self.assertEqual(bytes(c.mem_read(0x06000000,0x20000)),b'\xa6'*0x20000)

    def test_guard_rejects_another_revision(self):
        changed=bytearray(self.baseline);changed[0x26024]^=1
        with self.assertRaisesRegex(ValueError,'exact v0.9'):plans(bytes(changed))

    def test_only_declared_rom_ranges_change(self):
        owned={i for w in self.writes for i in range(w.offset,w.end)}
        self.assertEqual(len(self.target),len(self.baseline))
        self.assertTrue(all(i in owned for i,(a,b) in enumerate(zip(self.baseline,self.target)) if a!=b))


if __name__=='__main__':unittest.main()
