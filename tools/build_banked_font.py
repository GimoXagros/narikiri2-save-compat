#!/usr/bin/env python3
"""Non-distribution integration build for the complete-syllable font engine.

The visual transcription is experimental input, never release-approved prose.
Every source change has an exact expected value and a nonoverlapping owner.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
import struct
import tempfile

from build_compact_target_catalog import known_compact_labels
from extended_compact_spec import extended_fields, text_at, validate_tables
from transcribe_compact_font import transcribe, READINGS
from narikiri2_text_spec import BASELINE_SHA256, hangul_to_game_code, single_byte_to_game_code
from import_dalmoori_8x8 import import_characters, PINNED_COMMIT
from build_dalmoori_gba_font import read_bitmap, place, pack_4bpp, unpack_4bpp
from private_font_spec import Write, HOOKS, veneer
from verify_save_fix_guard import verify_save_fix_bytes
from bps import create_bps, apply_bps
from confirmed_text_edits import plans as full_text_plans, encode_full
from find_gba_lz77_asset import decompress_lz77_stream
from narikiri2_item_ui_font import compress_lz77
from fixed_ui_labels import LABELS, plans as fixed_ui_plans
from reference_prose_names import plans as reference_prose_plans
from legacy_dalmoori_font import bitmaps as legacy_bitmaps
from translated_ui_graphics import plans as graphic_plans
from repair_reviewed_script_records import plans as script_repair_plans

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SIZE, TARGET_SIZE = 0xC00000, 0xC20000
FFR_HASH = 'f94cb5a128c8a98e6e18e6a0598ebf9b266f54da0750367af8defac3eb2df7d4'
UNRESOLVED = {'ITEM_000','JOB_199','JOB_200','MONSTER_000','ARTE_056',
              'ARTE_209','BATTLE_NAME_046','BATTLE_NAME_049','BATTLE_NAME_057'}
EXPLICIT_NAMES = {'JOB_000':'없음','JOB_199':'비숍','JOB_200':'비숍',
    'MONSTER_000':'없음','ARTE_000':'없음','ARTE_056':'파이어볼','ARTE_209':'파이어볼',
    'BATTLE_NAME_046':'로스','BATTLE_NAME_049':'샘','BATTLE_NAME_057':'알'}
FORMAT = re.compile(r'%[0-9]*[dslkh]')
FIXED_NAME_FIELDS = {0x9780,0x9788}


def units(text):
    position=0
    while position<len(text):
        if text[position]=='%':
            match=FORMAT.match(text,position)
            if not match:raise ValueError('Unresolved format directive')
            yield match[0];position=match.end()
        else:
            char=text[position]
            if not ('가'<=char<='힣' or char=='\n' or 0x20<=ord(char)<0x7f):
                raise ValueError(f'Unresolved Unicode character {char!r}')
            yield char;position+=1


def requires_private(char):
    return len(char)==1 and char!='\n' and READINGS.get(ord(char)-0x10)!=char


def large_code(char):
    if '가'<=char<='힣':return hangul_to_game_code(char)
    if len(char)==1 and 0x21<=ord(char)<=0x7e:
        return int.from_bytes(chr(ord(char)+0xfee0).encode('cp932'),'big')
    raise ValueError(f'No existing full-width glyph for {char!r}')


def encode(text,index):
    return b''.join(token(index[u]) if u in index else u.encode('ascii') for u in units(text))


def collect_ui(source):
    authored=json.loads((ROOT/'translation/banked_ui_text.json').read_text(encoding='utf-8'))
    original=json.loads((ROOT/'config/ui_source_bindings.json').read_text(encoding='utf-8'))
    if len(original)!=188 or set(authored)!=set(original):
        raise ValueError('Residual UI population mismatch')
    result=[]
    for storage_hex,row in original.items():
        storage=int(storage_hex,16)
        pointer,raw=text_at(source,storage)
        if digest(raw)!=row['sha256'] or pointer!=int(row['pointer'],16):
            raise ValueError('Residual source binding mismatch')
        if storage==0xA1E4:
            # This is an eight-byte CpuSet save signature, not display text.
            # Relocation to an unaligned string pool changes the copied words
            # and makes the next cold boot reject an apparently successful save.
            if pointer!=0x089513E8 or raw!=b'NARIKIRI':
                raise ValueError('Protected save-signature source changed')
            continue
        if storage==0x188C38:
            # This pointer-shaped sample belongs to the referenced PCM wave
            # 188AD8..189C4D. FFR's value happens to name a play-time template;
            # it has no text consumer. Keep the entire sound area byte-identical.
            if pointer!=0x08951B48:raise ValueError('PCM sample baseline changed')
            continue
        if storage in FIXED_NAME_FIELDS and len(raw)!=3:
            raise ValueError('Default-name initializer source changed')
        text=authored[storage_hex]
        old_formats=FORMAT.findall(raw.decode('latin1'))
        new_formats=FORMAT.findall(text)
        if [x for x in old_formats if x!='%h']!=new_formats:
            raise ValueError(f"{storage_hex}: control/argument signature changed")
        list(units(text))
        result.append(dict(id='UI_'+storage_hex,category='UI',storage=storage,
            source_pointer=pointer,source_hex=raw.hex(),text=text,
            review_status='INDIVIDUAL_SOURCE_REVIEW_CONSUMER_RUNTIME_PENDING'))
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def assemble(path, offset, count, limit=256):
    from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
    source = path.read_text(encoding='utf-8').replace('FONT_COUNT', str(count))
    payload = bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(source, addr=0x08000000+offset)[0])
    if not 0 < len(payload) <= limit:
        raise ValueError(f'Assembly allocation overflow: {path.name}')
    lines = source.split('.balign', 1)[0].splitlines()
    count = sum(bool(s.strip()) and not s.strip().endswith(':') for s in lines)
    insns = list(Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(payload, 0x08000000+offset))[:count]
    if len(insns) != count or any(i.size != 2 and i.mnemonic != 'bl' for i in insns):
        raise ValueError(f'Thumb-1 boundary failure: {path.name}')
    if any(i.mnemonic in ('blx','it','itt','cbz','cbnz','movw','movt','nop') for i in insns):
        raise ValueError(f'ARM7TDMI profile failure: {path.name}')
    return payload


def token(index):
    if not 0 <= index < 31*31:
        raise ValueError('Token index out of range')
    return bytes((0x7f, index//31+1, index%31+1))


def collect(source):
    validate_tables(source)
    fields = {p:(name,name.split('_')[0]) for p,name in known_compact_labels().items()}
    fields.update(extended_fields())
    with (ROOT/'translation/complete_item_edits.csv').open(encoding='utf-8-sig',newline='') as f:
        edits = {f"ITEM_{int(r['entry_index']):03d}":r for r in csv.DictReader(f)}
    with (ROOT/'translation/banked_item_names.tsv').open(encoding='utf-8-sig',newline='') as f:
        item_rows=list(csv.DictReader(f,delimiter='\t'))
    if len(item_rows)!=157 or {r['id'] for r in item_rows}!={f'ITEM_{i:03d}' for i in range(157)}:
        raise ValueError('Authored item-name population changed')
    authored={r['id']:r['text'] for r in item_rows}
    for filename,count in (('job',201),('monster',165),('arte',232),('misc',107),('selector',365)):
        with (ROOT/f'translation/banked_{filename}_names.tsv').open(encoding='utf-8-sig',newline='') as f:
            entries=list(csv.DictReader(f,delimiter='\t'))
        if len(entries)!=count or len({r['id'] for r in entries})!=count:
            raise ValueError(f'{filename}: authored population mismatch')
        for row in entries:
            if row['id'] in authored:raise ValueError('Duplicate authored identity')
            authored[row['id']]=row['text']
    if set(authored)!={identity for identity,_ in fields.values()}:
        raise ValueError('Authored name identities do not cover the exact physical tables')
    rows, unresolved = [], []
    for storage,(identity,category) in sorted(fields.items()):
        pointer, raw = text_at(source,storage)
        result = transcribe(raw)
        if identity in authored:
            wording=authored[identity]
            status='INDIVIDUAL_SOURCE_CONTEXT_REVIEW_RUNTIME_PENDING'
        elif identity in edits:
            edit = edits[identity]
            if raw != bytes.fromhex(edit['expected_raw_hex']):
                raise ValueError(f'{identity}: authored edit source changed')
            wording = edit['final_korean']
            status = edit['status']
        elif (result['unsupported'] or result['uncomposed_jamo'] or any(
                u['kind']=='format' and u['raw_hex']!='2568' for u in result['units'])):
            unresolved.append(identity)
            continue
        else:
            wording = result['text']
            status = 'PROVISIONAL_VISUAL_TRANSCRIPTION'
        if not wording or any(not ('가'<=c<='힣' or 0x20<=ord(c)<0x7f) for c in wording):
            raise ValueError(f'{identity}: unresolved output character {wording!r}')
        rows.append(dict(id=identity,category=category,storage=storage,source_pointer=pointer,
                         source_hex=raw.hex(),text=wording,review_status=status))
    if unresolved or len(rows)!=1227:
        raise ValueError(f'Unresolved population changed: {unresolved}')
    return rows+collect_ui(source), []


def prepare_fonts(rows, folder):
    texts=[r['text'] for r in rows]+[r[3] for r in LABELS]
    required = {c for text in texts for c in units(text) if requires_private(c)}
    # Private tokens are stored in EEPROM names. Never derive their indices
    # from the current vocabulary: insertion/removal would reinterpret saves.
    lock = json.loads((ROOT/'config/private_glyph_order.json').read_text(encoding='utf-8'))
    chars = lock['glyphs']
    if len(chars)!=len(set(chars)) or not required.issubset(chars):
        raise ValueError('Private glyph registry collision or missing glyph; append without renumbering')
    if len(chars)>512:
        raise ValueError('Font ROM allocation capacity exceeded')
    manifest = import_characters(ROOT/'third_party/_work/dalmoori-font', folder, chars)
    clear, solid, codes = bytearray(), bytearray(), bytearray()
    for char,row in zip(chars,manifest):
        if row['unicode'] != f'U+{ord(char):04X}':
            raise ValueError('Importer ordering mismatch')
        bitmap = place(read_bitmap(folder/'glyphs'/(row['unicode']+'.txt')))
        for bg,bank in ((0,clear),(11,solid)):
            tile = pack_4bpp(bitmap,bg,15)
            if unpack_4bpp(tile,bg,15)!=bitmap:
                raise ValueError('Tile round trip failed')
            bank.extend(tile)
        codes.extend(large_code(char).to_bytes(2,'big'))
    return chars, bytes(clear), bytes(solid), bytes(codes)


def ascii_font(source):
    original,consumed=decompress_lz77_stream(source,0xCA3F4,0x10000)
    if len(original)!=8192 or consumed!=1769:raise ValueError('Small-font profile mismatch')
    selected=dict(READINGS)
    modified=bytearray(original)
    for tile,bitmap in legacy_bitmaps().items():
        packed=pack_4bpp(bitmap,0,15)
        if unpack_4bpp(packed,0,15)!=bitmap:raise ValueError('Legacy glyph pixel round-trip failed')
        modified[tile*32:tile*32+32]=packed
    for tile in set(range(256))-set(selected):
        if modified[tile*32:tile*32+32]!=original[tile*32:tile*32+32]:
            raise ValueError('Functional or unresolved font tile changed')
    compressed=compress_lz77(bytes(modified),vram_safe=True)
    if len(compressed)>0x2000 or decompress_lz77_stream(compressed,0,0x10000)[0]!=bytes(modified):
        raise ValueError('Relocated font compression bound or round-trip failed')
    return compressed,bytes(modified),selected


def full_name_plans(source):
    with (ROOT/'translation/banked_full_names.tsv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    expected={0x2B580C+i*64 for i in range(201)}|{0x374A38+i*20+4 for i in range(232)}|{0x9784,0x978C}
    if len(rows)!=435 or {int(r['storage'],16) for r in rows}!=expected:
        raise ValueError('Full-name physical population mismatch')
    result=[]
    for row in rows:
        storage=int(row['storage'],16)
        pointer,raw=text_at(source,storage)
        if pointer!=int(row['source_pointer'],16) or digest(raw)!=row['source_sha256']:
            raise ValueError(f"{row['id']}: full-name source binding mismatch")
        # These are names, with no format directives. Punctuation must use a
        # complete existing glyph, not a compact fragment bearing its ASCII byte.
        if not row['text'] or len(row['text'])>10 or any(x in row['text'] for x in ('%','\n','@')):
            raise ValueError('Full-name vocabulary or measured column envelope changed')
        payload=b''.join(encode_full(ch) if ch==' ' or '가'<=ch<='힣' else
                         large_code(ch).to_bytes(2,'big') for ch in row['text'])
        if storage in (0x9784,0x978C) and len(payload)>6:
            raise ValueError('Default full-name initializer copies seven bytes including NUL')
        if storage in (0x9784,0x978C):
            payload=payload.ljust(6,b'\0')
        result.append(dict(id=row['id'],storage=storage,old_offset=pointer-0x08000000,payload=payload))
    return result


def build(source, rows, chars, clear, solid, codes):
    if len(source)!=SOURCE_SIZE or digest(source)!=BASELINE_SHA256:
        raise ValueError('Candidate A source identity mismatch')
    verify_save_fix_bytes(source)
    glyph_index = {c:i for i,c in enumerate(chars)}
    image = source + b'\xff'*(TARGET_SIZE-SOURCE_SIZE)
    writes = []
    def add(identity,category,offset,payload,expected=None):
        if expected is None:
            if offset<SOURCE_SIZE: raise ValueError('Original writes require exact expectations')
            expected = b'\xff'*len(payload)
        writes.append(Write(identity,category,offset,expected,payload))
    for oldname,offset,expected,destination,scratch in HOOKS[:4]:
        name = oldname.replace('private_','banked_')
        add(name,'hook',offset,veneer(offset,destination,scratch),bytes.fromhex(expected))
        add(name+'_body','assembly',destination,assemble(ROOT/'asm'/(name+'.s'),destination,len(chars)))
    for name,offset,limit in (('banked_decode',0xC00500,256),('banked_get_tile',0xC00600,256),
                              ('private_tile_cache',0xC00800,0x400),('banked_popup',0xC00C00,0x400)):
        add(name,'assembly',offset,assemble(ROOT/'asm'/(name+'.s'),offset,len(chars),limit))
    add('banked_popup_hook','hook',0x25D00,veneer(0x25D00,0xC00C00,3),bytes.fromhex('70B50E1C0023041D'))
    # Battle actors have an original ten-byte name field. A descriptor retains
    # a stable ROM/party-record string pointer without overwriting neighboring
    # actor fields. The two actual consumers resolve it before reading text.
    for name,offset in (('banked_actor_name_store',0xC1E800),('banked_actor_name_resolve',0xC1E880),
                        ('banked_actor_monster_init',0xC1E900),('banked_actor_party_init',0xC1E980),
                        ('banked_actor_small_entry',0xC1EA00),('banked_actor_format_string',0xC1EA80)):
        add(name,'assembly',offset,assemble(ROOT/'asm'/(name+'.s'),offset,len(chars),0x80))
    for name,entry,destination,expected in (
        ('actor_monster',0x1DC68,0xC1E900,'316888F091FF5048'),
        ('actor_party',0x1D758,0xC1E980,'814689F019FA2E49'),
        ('actor_small',0x1AC8,0xC1EA00,'F0B581B0051C0091'),
        ('actor_format_string',0x25D8,0xC1EA80,'70B5041C0D1C00F061F9')):
        original=bytes.fromhex(expected)
        add(name+'_hook','hook',entry,veneer(entry,destination,3).ljust(len(original),b'\0'),original)
    for name,entry,destination,expected,limit in (
        ('banked_name_import',0x1A25C,0xC01000,'70B5051C0C1C1821',0x200),
        ('banked_name_commit',0x1A1F0,0xC01200,'002E03D000261220',0x100),
        ('banked_name_init_first',0x9720,0xC01400,'2068174909680160',0x80),
        ('banked_name_init_second',0x9734,0xC01480,'14490968C1634F30',0x80)):
        add(name+'_hook','hook',entry,veneer(entry,destination,3),bytes.fromhex(expected))
        add(name,'assembly',destination,assemble(ROOT/'asm'/(name+'.s'),destination,len(chars),limit))
    # Six editor cells hold up to 18 compact bytes. 0501C's third argument
    # allocates/checks the formatted INPUT scratch, not the final name field.
    # The output remains six complete glyphs plus NUL in the original 13 bytes.
    add('name_commit_input_scratch','hook',0x1A24C,bytes.fromhex('1322'),bytes.fromhex('0D22'))
    add('battle_font_upload_hook','hook',0x1F28,veneer(0x1F28,0xC1EB00,3),bytes.fromhex('F022120101F0FCF8'))
    add('battle_font_upload','assembly',0xC1EB00,assemble(ROOT/'asm/banked_battle_font_upload.s',0xC1EB00,len(chars),0x80))
    add('diagnostic_failure_stop','assembly',0xC00700,b'\xfe\xe7')
    add('dalmoori_clear','font',0xC02000,clear)
    add('dalmoori_solid','font',0xC06000,solid)
    add('existing_large_code_map','mapping',0xC0A000,codes)
    for row in graphic_plans(source,ROOT):
        add(row['id'],row['category'],row['offset'],row['payload'],row['expected'])
    ascii_stream,_,_=ascii_font(source)
    add('ascii_dalmoori_font_stream','font',0xC18000,ascii_stream)
    for offset in (0x2158,0x21D4):
        add(f'ascii_loader_{offset:X}','pointer',offset,struct.pack('<I',0x08C18000),
            struct.pack('<I',0x080CA3F4))
    cursor, aliases = 0xC0A400, {}
    for row in rows:
        raw = encode(row['text'],glyph_index)
        if row['storage'] in FIXED_NAME_FIELDS and (len(raw)>=19 or len(row['text'])>6):
            raise ValueError('Default protagonist name exceeds committed record bounds')
        if row['category']!='UI' and (len(raw)>=32 or len(row['text'])*2>=32):
            raise ValueError(f"{row['id']}: input or popup bound exceeded")
        if len(raw)>=256:raise ValueError(f"{row['id']}: formatter scratch bound exceeded")
        key = (row['source_pointer'],raw)
        if key not in aliases:
            aliases[key] = cursor
            add(row['id']+'_text','text',cursor,raw+b'\0')
            cursor += len(raw)+1
        target = aliases[key]
        add(row['id']+'_pointer','pointer',row['storage'],struct.pack('<I',0x08000000+target),
            struct.pack('<I',row['source_pointer']))
        row.update(target=target,raw_hex=raw.hex())
    for row in full_text_plans(source,ROOT)+full_name_plans(source)+fixed_ui_plans(source,lambda text:encode(text,glyph_index))+reference_prose_plans(source)+script_repair_plans(source,ROOT):
        add(row['id']+'_pointer','pointer',row['storage'],struct.pack('<I',0x08000000+cursor),
            struct.pack('<I',0x08000000+row['old_offset']))
        add(row['id']+'_payload','full_text',cursor,row['payload']+b'\0')
        cursor+=len(row['payload'])+1
    writes.sort(key=lambda w:w.offset)
    previous = 0
    for w in writes:
        if w.offset<previous or w.end>TARGET_SIZE or len(w.expected)!=len(w.final):
            raise ValueError(f'{w.identity}: overlapping or out-of-bounds writer')
        if image[w.offset:w.end]!=w.expected:
            raise ValueError(f'{w.identity}: expected bytes mismatch')
        previous = w.end
    result = bytearray(image)
    for w in writes: result[w.offset:w.end] = w.final
    previous = 0
    for w in writes:
        if result[previous:w.offset]!=image[previous:w.offset] or result[w.offset:w.end]!=w.final:
            raise ValueError('Unowned difference or failed write')
        previous = w.end
    if result[previous:]!=image[previous:] or result[0xAC3F4:0xCB000]!=source[0xAC3F4:0xCB000]:
        raise ValueError('Original font or trailing allocation changed')
    if result[0xCB000:0x2B2CAC]!=source[0xCB000:0x2B2CAC]:
        raise ValueError('Protected sound assets changed')
    result = bytes(result)
    verify_save_fix_bytes(result,expected_size=TARGET_SIZE)
    return result, writes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True)
    args = p.parse_args()
    if args.output_dir.exists(): raise ValueError('Output folder must be new')
    source = (ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
    if digest(source)!=BASELINE_SHA256: raise ValueError('Candidate identity mismatch')
    ffrs = [x for x in ROOT.glob('*.gba') if x.stat().st_size==SOURCE_SIZE and digest(x.read_bytes())==FFR_HASH]
    if len(ffrs)!=1: raise ValueError('Exact FFR source not found uniquely')
    ffr = ffrs[0].read_bytes()
    rows, unresolved = collect(source)
    args.output_dir.mkdir(parents=True)
    chars,clear,solid,codes = prepare_fonts(rows,args.output_dir/'font')
    target,writes = build(source,rows,chars,clear,solid,codes)
    second,_ = build(source,[dict(r) for r in rows],chars,clear,solid,codes)
    if target!=second: raise ValueError('Nondeterministic build')
    patch = create_bps(ffr,target)
    if apply_bps(ffr,patch)!=target or create_bps(ffr,target)!=patch:
        raise ValueError('BPS round-trip or determinism failed')
    (args.output_dir/'NARIKIRI2_BANKED_ENGINE_DIAGNOSTIC.gba').write_bytes(target)
    (args.output_dir/'NARIKIRI2_BANKED_ENGINE_DIAGNOSTIC_FROM_FFR.bps').write_bytes(patch)
    with (args.output_dir/'names.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report=dict(schema='narikiri2-banked-engine-v1',status='NON_DISTRIBUTION_ENGINE_DIAGNOSTIC',
        release_ready=False,source_rom_sha256=FFR_HASH,target_rom_sha256=digest(target),
        target_rom_size=len(target),patch_sha256=digest(patch),patch_size=len(patch),
        dalmoori_commit=PINNED_COMMIT,glyphs=chars,glyph_count=len(chars),physical_name_fields=1227,
        residual_ui_reference_candidates=188,physical_fields=len(rows),
        non_text_candidates_preserved=['0000A1E4: aligned eight-byte save signature','00188C38: PCM waveform sample, not a text pointer'],
        default_name_storage='Six editor cells; compact 19 bytes; full 13 bytes; bounded initializer and token-aware import/commit',
        full_name_fields=435,
        fixed_ui_label_fields=len(LABELS),
        reference_prose_name_records=len(reference_prose_plans(source)),
        converted_fields=len(rows),unresolved_fields=unresolved,save_guard='PASS',
        original_font_identity='PASS',unexpected_diff=0,deterministic='PASS',bps_roundtrip='PASS',
        ascii_font_relocation='Two original loader pointers; 217 identified text cells use native Dalmoori glyphs/components; 39 other cells preserved',
        runtime_status='NOT_VERIFIED',
        failure_behavior='Diagnostic stop at 08C00700; capacity exhaustion must fail testing',
        limitations=['Authored name tables need current-artifact menu/battle layout verification',
            'Residual compact reference consumer classification and runtime verification remain open',
            'Enumerated names/UI are converted; remaining consumers, graphics and dialogue scope remain under audit',
            'Screen working-set capacity, other layouts and dynamic consumers remain unverified'],
        writes=[dict(id=w.identity,category=w.category,offset=w.offset,end=w.end,
                     source_sha256=digest(w.expected),target_sha256=digest(w.final)) for w in writes])
    (args.output_dir/'BUILD_MANIFEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('writes','glyphs')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
