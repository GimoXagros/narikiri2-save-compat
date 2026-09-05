"""Execute both font cache profiles on ARM with guarded memory ownership."""
import struct
from pathlib import Path
import unittest

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R4, UC_ARM_REG_R5,
    UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_SP, UC_ARM_REG_LR,
    UC_ARM_REG_PC, UC_ARM_REG_CPSR)

ROOT = Path(__file__).resolve().parents[1]


class TileCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly = (ROOT/"asm/private_tile_cache.s").read_text(encoding="utf-8")
        cls.code = bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(cls.assembly, addr=0x08C00000)[0])

    def setUp(self):
        self.cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        for base,size in ((0x08C00000,0x10000),(0x03000000,0x8000),(0x04000000,0x1000),(0x06000000,0x20000)):
            self.cpu.mem_map(base,size)
        self.cpu.mem_write(0x08C00000,self.code)
        self.cpu.mem_write(0x03000010,struct.pack("<H",0x100))
        self.cpu.mem_write(0x0300004C,struct.pack("<III",0x0600F800,0x0600C000,0))
        self.cpu.mem_write(0x0600EF00,b"\x55"*(72*32))
        self.glyph=bytes(range(32))
        self.cpu.mem_write(0x08C01000,self.glyph)

    def run_cache(self):
        c=self.cpu
        c.reg_write(UC_ARM_REG_CPSR,0x3f)
        c.reg_write(UC_ARM_REG_SP,0x03007E00)
        c.reg_write(UC_ARM_REG_LR,0x08C00801)
        c.reg_write(UC_ARM_REG_R0,0x08C01000)
        saved=(UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7)
        for i,r in enumerate(saved):c.reg_write(r,0x11110000+i)
        c.emu_start(0x08C00001,0x08C00800,count=100000)
        self.assertEqual(c.reg_read(UC_ARM_REG_PC),0x08C00800)
        self.assertEqual(c.reg_read(UC_ARM_REG_SP),0x03007E00)
        for i,r in enumerate(saved):self.assertEqual(c.reg_read(r),0x11110000+i)
        return c.reg_read(UC_ARM_REG_R0)

    def test_thumb1_instruction_boundaries(self):
        lines=self.assembly.split('.balign',1)[0].splitlines()
        count=sum(bool(s.strip()) and not s.strip().endswith(':') for s in lines)
        instructions=list(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(self.code,0x08C00000))[:count]
        self.assertEqual(len(instructions),count)
        for i in instructions:
            self.assertTrue(i.size==2 or i.mnemonic=='bl',(i.mnemonic,i.op_str))
            self.assertNotIn(i.mnemonic,('blx','it','cbz','cbnz','movw','movt'))

    def test_first_free_slot_and_font_tilemap_guards(self):
        before=bytes(self.cpu.mem_read(0x06000000,0x20000))
        self.assertEqual(self.run_cache(),0x178)
        after=bytes(self.cpu.mem_read(0x06000000,0x20000))
        self.assertEqual(after[:0xEF00],before[:0xEF00])
        self.assertEqual(after[0xEF00:0xEF20],self.glyph)
        self.assertEqual(after[0xEF20:],before[0xEF20:])

    def test_retained_shadow_and_visible_references_are_both_pinned(self):
        # Include palette and flip bits; the lower ten bits select the tile.
        self.cpu.mem_write(0x03000058,struct.pack('<H',0xF578))
        self.cpu.mem_write(0x0600F800,struct.pack('<H',0xA979))
        self.assertEqual(self.run_cache(),0x17A)
        self.assertEqual(bytes(self.cpu.mem_read(0x0600EF00,64)),b'\x55'*64)

    def test_identical_live_glyph_reused_even_when_every_slot_is_pinned(self):
        self.cpu.mem_write(0x03000058,struct.pack('<72H',*range(0x178,0x1C0)))
        self.cpu.mem_write(0x0600EF00+71*32,self.glyph)
        before=bytes(self.cpu.mem_read(0x06000000,0x20000))
        self.assertEqual(self.run_cache(),0x1BF)
        self.assertEqual(bytes(self.cpu.mem_read(0x06000000,0x20000)),before)

    def test_capacity_exhaustion_is_atomic_and_explicit(self):
        self.cpu.mem_write(0x03000058,struct.pack('<72H',*range(0x178,0x1C0)))
        before=bytes(self.cpu.mem_read(0x06000000,0x20000))
        self.assertEqual(self.run_cache(),0xFFFFFFFF)
        self.assertEqual(bytes(self.cpu.mem_read(0x06000000,0x20000)),before)

    def test_battle_cache_preserves_banner_and_spell_map(self):
        self.cpu.mem_write(0x03000010,struct.pack('<H',0x1341))
        self.cpu.mem_write(0x0600E000,b'\x55'*0x1800)
        self.cpu.mem_write(0x03000058,struct.pack('<H',0xF540))
        self.cpu.mem_write(0x0600F800,struct.pack('<H',0xA941))
        before=bytes(self.cpu.mem_read(0x06000000,0x20000))
        self.assertEqual(self.run_cache(),0x142)
        after=bytes(self.cpu.mem_read(0x06000000,0x20000))
        self.assertEqual(after[:0xE840],before[:0xE840])
        self.assertEqual(after[0xE840:0xE860],self.glyph)
        self.assertEqual(after[0xE860:],before[0xE860:])

    def test_other_layouts_or_palette_modes_do_not_write(self):
        for address,value in ((0x03000050,0x06008000),(0x0300004C,0x0600F000),
                              (0x03000054,1),(0x0300145A,3)):
            old=bytes(self.cpu.mem_read(address,4))
            self.cpu.mem_write(address,struct.pack('<I',value))
            before=bytes(self.cpu.mem_read(0x06000000,0x20000))
            self.assertEqual(self.run_cache(),0xFFFFFFFF)
            self.assertEqual(bytes(self.cpu.mem_read(0x06000000,0x20000)),before)
            self.cpu.mem_write(address,old)


if __name__ == '__main__':
    unittest.main()
