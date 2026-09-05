"""Run the real AN9J consumers; pixel expectations come from pinned bitmaps."""
import csv
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_banked_font import collect, prepare_fonts, build, token, TARGET_SIZE, large_code, units, encode
from narikiri2_text_spec import hangul_to_game_code, single_byte_to_game_code
from extended_compact_spec import text_at, extended_fields
from build_compact_target_catalog import known_compact_labels
from verify_save_fix_guard import verify_save_fix_bytes, SaveFixGuardError
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import *


class BankedFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        cls.rows,cls.unresolved=collect(cls.source)
        cls.temp=tempfile.TemporaryDirectory()
        cls.chars,cls.clear,cls.solid,cls.codes=prepare_fonts(cls.rows,Path(cls.temp.name)/'font')
        cls.target,cls.writes=build(cls.source,cls.rows,cls.chars,cls.clear,cls.solid,cls.codes)
        cls.index={c:i for i,c in enumerate(cls.chars)}

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def cpu(self,rom=None):
        c=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
        for base,size in ((0x08000000,0x1000000),(0x02000000,0x40000),(0x03000000,0x8000),
                          (0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000)):
            c.mem_map(base,size)
        c.mem_write(0x08000000,self.target if rom is None else rom)
        return c

    def reset(self,c,mode=0):
        c.mem_write(0x03000000,b'\0'*0x8000)
        c.mem_write(0x02000000,b'\0'*0x4000)
        c.mem_write(0x06000000,b'\0'*0x20000)
        c.mem_write(0x0300004c,struct.pack('<III',0x0600f800,0x0600c000,0))
        c.mem_write(0x0300145a,bytes((mode,)))
        c.mem_write(0x03000010,struct.pack('<H',0x100))
        c.reg_write(UC_ARM_REG_CPSR,0x3f)
        c.reg_write(UC_ARM_REG_SP,0x03007e00)
        c.reg_write(UC_ARM_REG_LR,0x02020001)

    def run_cpu(self,c,start,stop=0x02020000):
        c.emu_start(start|1,stop,count=1000000)
        self.assertEqual(c.reg_read(UC_ARM_REG_PC),stop,'Diagnostic failure or invalid continuation')

    def render(self,c,raw,simple=False,mode=0,reset=True,x=0,y=0):
        if reset:self.reset(c,mode)
        c.reg_write(UC_ARM_REG_SP,0x03007e00)
        c.reg_write(UC_ARM_REG_LR,0x02020001)
        c.mem_write(0x02001000,raw+b'\0')
        if simple:
            c.reg_write(UC_ARM_REG_R0,x);c.reg_write(UC_ARM_REG_R1,y)
            c.reg_write(UC_ARM_REG_R2,0x02001000)
            self.run_cpu(c,0x08001df0)
        else:
            c.mem_write(0x02000100,bytes((x,y,30,20,0,0,0,15,0,0,0,0)))
            c.reg_write(UC_ARM_REG_R0,0x02000100);c.reg_write(UC_ARM_REG_R1,0x02001000)
            self.run_cpu(c,0x08001ac8)
        self.assertEqual(c.reg_read(UC_ARM_REG_SP),0x03007e00)
        return bytes(c.mem_read(0x03000058,0x500))

    def assert_pixels(self,c,shadow,text,mode=0):
        bank=self.solid if mode==11 else self.clear
        for i,char in enumerate(text):
            tile=struct.unpack_from('<H',shadow,i*2)[0]&0x3ff
            if char in self.index:
                idx=self.index[char]
                self.assertTrue(0x178<=tile<0x1c0,(char,tile))
                self.assertEqual(bytes(c.mem_read(0x0600c000+tile*32,32)),bank[idx*32:(idx+1)*32],char)
            else:self.assertEqual(tile,ord(char)-0x10)

    def test_every_name_small_and_simple_bitmap_and_advance(self):
        c=self.cpu()
        for simple in (False,True):
            for row in self.rows:
                if row['category']=='UI':continue
                with self.subTest(id=row['id'],simple=simple):
                    shadow=self.render(c,bytes.fromhex(row['raw_hex']),simple)
                    self.assert_pixels(c,shadow,row['text'])
                    if not simple:self.assertEqual(c.mem_read(0x02000104,1)[0],len(row['text']))

    def test_all_glyphs_both_palette_modes(self):
        c=self.cpu()
        for mode in (0,11):
            for i,char in enumerate(self.chars):
                shadow=self.render(c,token(i),mode=mode)
                self.assert_pixels(c,shadow,char,mode)

    def test_original_1227_name_paths_unchanged(self):
        old,new=self.cpu(self.source),self.cpu()
        fields=set(known_compact_labels())|set(extended_fields())
        for storage in sorted(fields):
            raw=text_at(self.source,storage)[1]
            with self.subTest(storage=hex(storage)):
                self.assertEqual(self.render(old,raw),self.render(new,raw))

    def test_decoder_bounds_and_registers(self):
        c=self.cpu()
        for idx in range(len(self.chars)):
            self.reset(c);c.mem_write(0x02001000,token(idx))
            c.reg_write(UC_ARM_REG_R0,0x02001000)
            self.run_cpu(c,0x08c00500)
            self.assertEqual(c.reg_read(UC_ARM_REG_R0),idx)
        for raw in (b'\x7f\0\1',b'\x7f\1\0',b'\x7f\x20\1',token(len(self.chars)),b'abc'):
            self.reset(c);c.mem_write(0x02001000,raw);c.reg_write(UC_ARM_REG_R0,0x02001000)
            self.run_cpu(c,0x08c00500)
            self.assertEqual(c.reg_read(UC_ARM_REG_R0),0xffffffff)

    def test_save_magic_is_not_relocated_as_display_text(self):
        self.assertEqual(self.target[0xa1e4:0xa1e8],self.source[0xa1e4:0xa1e8])
        self.assertEqual(self.target[0x9513e8:0x9513f0],b'NARIKIRI')
        bad=bytearray(self.target)
        bad[0xa1e4:0xa1e8]=struct.pack('<I',0x08c0d606)
        with self.assertRaises(SaveFixGuardError):verify_save_fix_bytes(bytes(bad),expected_size=TARGET_SIZE)

    def test_popup_every_name_output_and_sentinels(self):
        c=self.cpu()
        for row in self.rows:
            if row['category']=='UI':continue
            with self.subTest(id=row['id']):
                self.reset(c)
                c.mem_write(0x02000800,b'\xa5'*0x100)
                c.mem_write(0x02001000,bytes.fromhex(row['raw_hex'])+b'\0')
                c.reg_write(UC_ARM_REG_R0,0x02000800);c.reg_write(UC_ARM_REG_R1,0x02001000)
                self.run_cpu(c,0x08025d00)
                out=bytes(c.mem_read(0x02000800,0x100))
                expected=b''
                for char in row['text']:
                    code=(large_code(char) if char in self.index else
                          single_byte_to_game_code(self.source,char.encode('ascii'),0,0)[0])
                    expected+=code.to_bytes(2,'big')
                self.assertEqual(out[:4],b'\xa5'*4)
                padding=b'\x81\x40'*(9-(len(row['text'])+1)//2)
                content=expected if b'\x7f' in bytes.fromhex(row['raw_hex']) else bytes.fromhex(row['raw_hex'])
                self.assertEqual(out[4:4+len(padding+content)+1],padding+content+b'\0')
                self.assertEqual(out[0x24:],b'\xa5'*(0x100-0x24))

    def test_large_conversion_each_glyph_and_pointer_advance(self):
        # Stop before rendering pixels: this checks the shared code/advance boundary.
        for large in (False,True):
            c=self.cpu()
            for i,char in enumerate(self.chars):
                self.reset(c)
                c.mem_write(0x02001000,token(i)+b'\0')
                if large:
                    c.mem_write(0x03000040,bytes((0,0,20,10,0,0,0,0,0,0,0,0)))
                    c.reg_write(UC_ARM_REG_R4,0x02001000);c.reg_write(UC_ARM_REG_R6,0)
                    self.run_cpu(c,0x08001674,0x08001680)
                    self.assertEqual(c.reg_read(UC_ARM_REG_R4),0x02001002)
                else:
                    c.reg_write(UC_ARM_REG_R0,0x02001000);c.reg_write(UC_ARM_REG_R6,0x02001000)
                    c.reg_write(UC_ARM_REG_R8,0)
                    self.run_cpu(c,0x08005078,0x08005080)
                    self.assertEqual(c.reg_read(UC_ARM_REG_R6),0x02001003)
                expected=int.from_bytes(large_code(char).to_bytes(2,'big'),'little')
                self.assertEqual(c.reg_read(UC_ARM_REG_R0)&0xffff,expected)

    def test_visible_previous_page_retains_pixels(self):
        c=self.cpu()
        self.reset(c)
        first=self.chars[:30];second=self.chars[30:60]
        a=self.render(c,b''.join(token(self.index[ch]) for ch in first),reset=False)
        c.mem_write(0x0600f800,a)
        c.mem_write(0x03000058,b'\0'*0x500)
        old=bytes(c.mem_read(0x0600ef00,72*32))
        b=self.render(c,b''.join(token(self.index[ch]) for ch in second),reset=False)
        self.assert_pixels(c,a,''.join(first))
        self.assert_pixels(c,b,''.join(second))

    def test_actual_formatter_all_188_ui_templates(self):
        c=self.cpu()
        from build_banked_font import FORMAT
        for row in self.rows:
            if row['category']!='UI':continue
            with self.subTest(id=row['id']):
                self.reset(c)
                raw=bytes.fromhex(row['raw_hex'])
                c.mem_write(0x02001000,raw+b'\0')
                sample=encode('검은허리띠',self.index)
                c.mem_write(0x02003000,sample+b'\0')
                args=[];expected=b''
                for u in units(row['text']):
                    if u=='%l':expected+=b'\x10'
                    elif u=='%k':expected+=b'\x11'
                    elif u=='%s':args.append(0x02003000);expected+=sample
                    elif u.startswith('%'):
                        args.append(123)
                        width=int(u[1:-1] or '0')
                        expected+=str(123).rjust(width).encode('ascii')
                    else:expected+=encode(u,self.index)
                c.mem_write(0x02002000,struct.pack('<'+'I'*len(args),*args) or b'\0'*4)
                c.mem_write(0x02000400,b'\xa5'*512)
                c.reg_write(UC_ARM_REG_R0,0x02000400)
                c.reg_write(UC_ARM_REG_R1,0x02001000)
                c.reg_write(UC_ARM_REG_R2,0x02002000)
                self.run_cpu(c,0x08002648)
                out=bytes(c.mem_read(0x02000400,512))
                self.assertEqual(out[:len(expected)+1],expected+b'\0')
                self.assertEqual(out[len(expected)+1:],b'\xa5'*(511-len(expected)))

    def test_all_name_large_renderer_pixels_match_existing_complete_glyphs(self):
        a,b=self.cpu(),self.cpu()
        def render(c,raw):
            self.reset(c)
            c.mem_write(0x03000040,bytes((0,0,20,4,0,0,0,0,0,0,0,0)))
            c.mem_write(0x02001000,raw+b'\0')
            c.reg_write(UC_ARM_REG_R0,0x02001000)
            self.run_cpu(c,0x080015b8)
            return bytes(c.mem_read(0x03000040,0x1420))
        for row in self.rows:
            if row['category']=='UI':continue
            direct=b''.join((large_code(ch) if ch in self.index else
                single_byte_to_game_code(self.source,ch.encode('ascii'),0,0)[0]).to_bytes(2,'big')
                for ch in row['text'])
            with self.subTest(id=row['id']):
                self.assertEqual(render(a,bytes.fromhex(row['raw_hex'])),render(b,direct))

    def test_persisted_name_tokens_never_renumber(self):
        # Independent EEPROM values from the rev20 natural save/cold-load
        # evidence. Vocabulary edits must not reinterpret these saved names.
        self.assertEqual(encode('훌리오',self.index),bytes.fromhex('7f110a7f05157f0a12'))
        self.assertEqual(encode('캐로',self.index),bytes.fromhex('7f0d167f0503'))

    def test_sound_samples_are_never_relocated_as_text(self):
        # A source pointer-shaped word at 188C38 is PCM in the referenced
        # waveform 188AD8..189C4D. Assert the whole sound area, not one word.
        self.assertEqual(self.target[0xCB000:0x2B2CAC],self.source[0xCB000:0x2B2CAC])
        self.assertNotIn(0x188C38,{r['storage'] for r in self.rows})

    def test_battle_banner_top_and_bottom_use_only_sixty_tiles(self):
        # Both actual battle-popup branches25CDC/25CE6 pass one line to0F2C.
        # The constructor reuses a single type1 popup, clearing its old row.
        for y in (1,17):
            c=self.cpu();self.reset(c)
            c.mem_write(0x03000010,struct.pack('<H',0x1341))
            from unicorn import UC_HOOK_CODE
            def bios_fast_set(cpu,address,length,user):
                if address==0x080a6024:
                    src=cpu.reg_read(UC_ARM_REG_R0);dst=cpu.reg_read(UC_ARM_REG_R1);control=cpu.reg_read(UC_ARM_REG_R2)
                    count=control&0x1fffff
                    self.assertEqual(count%8,0)
                    raw=bytes(cpu.mem_read(src,4))*count if control&0x1000000 else bytes(cpu.mem_read(src,count*4))
                    cpu.mem_write(dst,raw);cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
            c.hook_add(UC_HOOK_CODE,bios_fast_set)
            c.reg_write(UC_ARM_REG_R0,y);c.reg_write(UC_ARM_REG_R1,1)
            self.run_cpu(c,0x08000f2c)
            shadow=bytes(c.mem_read(0x03000058,0x500))
            occupied=[t&1023 for t in struct.unpack('<640H',shadow) if 0x100<=t&1023<0x180]
            self.assertEqual(occupied,list(range(0x100,0x13c)))

    def test_battle_banner_upload_preserves_private_cache(self):
        from unicorn import UC_HOOK_CODE
        for mode,size in ((0,0xf00),(1,0x800)):
            c=self.cpu();self.reset(c)
            c.mem_write(0x03000010,struct.pack('<H',mode))
            source=bytes((i*17+3)&255 for i in range(0xf00))
            c.mem_write(0x02003000,source)
            c.mem_write(0x0600e000,b'\xa5'*0x1800)
            c.reg_write(UC_ARM_REG_R0,0x02003000);c.reg_write(UC_ARM_REG_R1,0x0600e000)
            def copy_call(cpu,address,length,user):
                if address==0x08003128:
                    self.assertEqual(cpu.reg_read(UC_ARM_REG_R2),size)
                    cpu.mem_write(cpu.reg_read(UC_ARM_REG_R1),bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R0),size)))
                    cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
            c.hook_add(UC_HOOK_CODE,copy_call)
            self.run_cpu(c,0x08001f28,0x08001f30)
            actual=bytes(c.mem_read(0x0600e000,0x1800))
            self.assertEqual(actual[:size],source[:size])
            self.assertEqual(actual[size:],b'\xa5'*(0x1800-size))

    def test_all_monster_actor_names_preserve_the_ten_byte_field(self):
        c=self.cpu()
        for monster in range(165):
            self.reset(c)
            actor=0x02010000
            c.mem_write(actor,b'\xa5'*0x180)
            c.reg_write(UC_ARM_REG_R7,actor);c.reg_write(UC_ARM_REG_R8,monster)
            self.run_cpu(c,0x0801DC58,0x0801DC76)
            actual=bytes(c.mem_read(actor,0x180))
            pointer,raw=text_at(self.target,0x2BF4D4+monster*52)
            expected=bytearray(b'\xa5'*0x180)
            if monster==164:
                self.assertEqual(raw,b'???')
                expected[0x13c:0x140]=b'???\0';expected[0x145]=0
            else:expected[0x13c:0x146]=struct.pack('<IIH',0x444e007f,pointer,0)
            self.assertEqual(actual,bytes(expected),monster)

    def test_party_actor_six_cell_names_and_both_consumers(self):
        c=self.cpu()
        for name in ('훌리오','캐로','훌리오BBB','가나다라마바','검은허리띠'):
            self.reset(c)
            raw=encode(name,self.index)
            actor=0x02010000;source=0x02003000
            c.mem_write(actor,b'\xa5'*0x180);c.mem_write(source,raw+b'\0')
            c.reg_write(UC_ARM_REG_R0,actor+0x13c);c.reg_write(UC_ARM_REG_R1,source)
            c.reg_write(UC_ARM_REG_R6,actor)
            self.run_cpu(c,0x0801D758,0x0801D766)
            actual=bytes(c.mem_read(actor,0x180));expected=bytearray(b'\xa5'*0x180)
            expected[0x13c:0x146]=struct.pack('<IIH',0x444e007f,source,0)
            expected[0x103]=0
            self.assertEqual(actual,bytes(expected),name)
            descriptor=actual[0x13c:0x146]
            shadow=self.render(c,descriptor,reset=False)
            self.assert_pixels(c,shadow,name)
            # The remaining actor-name consumer is the formatter's %s path.
            c.reg_write(UC_ARM_REG_SP,0x03007e00);c.reg_write(UC_ARM_REG_LR,0x02020001)
            c.mem_write(0x02001000,descriptor);c.mem_write(0x02002000,b'%s\0')
            c.mem_write(0x02002020,struct.pack('<I',0x02001000))
            c.mem_write(0x02000400,b'\xa5'*256)
            for reg,value in ((UC_ARM_REG_R0,0x02000400),(UC_ARM_REG_R1,0x02002000),(UC_ARM_REG_R2,0x02002020)):c.reg_write(reg,value)
            self.run_cpu(c,0x08002648)
            self.assertEqual(c.mem_read(0x02000400,len(raw)+1),raw+b'\0')
            self.assertEqual(c.mem_read(0x02000400+len(raw)+1,16),b'\xa5'*16)

    def test_new_game_names_fit_records_without_truncation(self):
        def initialize(c):
            self.reset(c)
            c.mem_write(0x02003000,b'\xa5'*0x100)
            c.mem_write(0x02003ff8,struct.pack('<I',0x02003000))
            c.reg_write(UC_ARM_REG_R4,0x02003ff8)
            self.run_cpu(c,0x08009720,0x08009744)
            return bytes(c.mem_read(0x02003000,0x100))
        actual=initialize(self.cpu())
        expected=bytearray(initialize(self.cpu(self.source)))
        for offset,name in ((0,'훌리오'),(60,'캐로')):
            raw=encode(name,self.index)+b'\0'
            expected[offset:offset+len(raw)]=raw
            full=b''.join(large_code(ch).to_bytes(2,'big') for ch in name)+b'\0'
            expected[offset+19:offset+26]=full.ljust(7,b'\0')
        self.assertEqual(actual,bytes(expected))

    def import_name(self,c,raw):
        self.reset(c)
        c.mem_write(0x02002000,b'\0'*32)
        c.mem_write(0x02001000,raw+b'\0')
        c.reg_write(UC_ARM_REG_R0,0x02002000)
        c.reg_write(UC_ARM_REG_R1,0x02001000)
        self.run_cpu(c,0x0801a25c,0x08019f48)
        return bytes(c.mem_read(0x02002000,32))

    def commit_name(self,c,slots):
        self.reset(c)
        c.mem_write(0x030029a8,struct.pack('<I',0x02004000))
        c.mem_write(0x02004000,b'\xa5'*64)
        c.mem_write(0x02002000,slots)
        c.mem_write(0x02000ffc,b'\xa5'*68)
        c.reg_write(UC_ARM_REG_R0,0x02002000)
        c.reg_write(UC_ARM_REG_R1,0x02001000)
        self.run_cpu(c,0x0801a1b0)
        self.assertEqual(c.mem_read(0x02000ffc,4),b'\xa5'*4)
        self.assertEqual(c.mem_read(0x02001020,32),b'\xa5'*32)
        scratch_end=int.from_bytes(c.mem_read(0x030029a8,4),'little')
        self.assertEqual(c.mem_read(scratch_end,16),b'\xa5'*16)
        return bytes(c.mem_read(0x02001000,32))

    def test_name_editor_legacy_import_commit_identity(self):
        a,b=self.cpu(self.source),self.cpu()
        for raw in (b'ABC123',b'\x12\xdc\xab',b',\xadj',
                    b'\x12\xb3\xde\xa1\x12ABC',b'A B  ',b'\xa1\xa2\xa3\xa4\xa5\xa6'):
            with self.subTest(raw=raw.hex()):
                old=self.import_name(a,raw);new=self.import_name(b,raw)
                self.assertEqual(old,new)
                self.assertEqual(self.commit_name(a,old),self.commit_name(b,new))

    def test_name_editor_private_and_mixed_six_slots(self):
        c=self.cpu()
        for text in ('훌리오','캐로','가나다라마바','검은허리띠'):
            raw=encode(text,self.index)
            slots=self.import_name(c,raw)
            self.assertEqual(slots[25],len(text))
            for i,ch in enumerate(text):
                self.assertEqual(slots[i*4:i*4+4],encode(ch,self.index)+b'\0')
            committed=self.commit_name(c,slots)
            self.assertEqual(committed[:len(raw)+1],raw+b'\0')
            expected=b''.join(large_code(ch).to_bytes(2,'big') for ch in text)+b'\0'
            self.assertEqual(committed[19:19+len(expected)],expected)
        # Private cells neither consume nor cancel the legacy kana mode.
        t=token(self.index['검'])
        raw=b'\x12\xb3\xde'+t+b'\xa1'+t+b'\xb3\xdf'+t
        slots=self.import_name(c,raw)
        self.assertEqual(slots[25],6)
        committed=self.commit_name(c,slots)
        self.assertEqual(committed[:len(raw)+1],raw+b'\0')


if __name__=='__main__':unittest.main()
