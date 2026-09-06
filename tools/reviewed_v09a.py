"""Strict second stage over frozen v0.9; source-bound authored prose and inspect fix."""
import hashlib,json,re,struct
from pathlib import Path
from confirmed_text_edits import encode_full,normalized
from narikiri2_text_spec import decode_game_text,read_c_string
from inspect_text_fix import plans as inspection_plans,V09_SHA256
from build_banked_font import encode

ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def tokens(text):return re.findall(r'@[A-Za-z]|%[0-9]*[A-Za-z]',text)
def numbers(text):return re.findall(r'[0-9０-９]+',text)

# Observed inventory description consumer: 18 full-width cells, two rows.
# A third wrapped row scrolls the first row out of the window.
ITEM_DESCRIPTION_BINDINGS={0x2B2CAC+i*0x14+0x10 for i in range(157)}
def validate_layout(identity,bindings,text):
    if ITEM_DESCRIPTION_BINDINGS.intersection(bindings):
        lines=text.split('\n')
        if len(lines)>2 or any(len(line)>18 for line in lines):
            raise ValueError('Item description exceeds 18 x 2 window '+identity)

def build(source,ledger=None):
    if sha(source)!=V09_SHA256:raise ValueError('Exact frozen v0.9 required')
    if ledger is None:ledger=json.loads((ROOT/'translation/v09a_reviewed_deltas.json').read_text(encoding='utf-8'))
    if (ledger['baseline_sha256'],ledger['population'],ledger['pointer_bindings'])!=(V09_SHA256,8038,8946):raise ValueError('Review population mismatch')
    if len(ledger['rows'])!=8038:raise ValueError('Incomplete or duplicate review')
    return build_bound(source, ledger, inspection_plans(source))


def build_bound(source, ledger, inspection_writes):
    """Apply a complete ledger bound to its own exact intermediate artifact.

    Revision adapters must independently rebind and review every source record.
    The frozen v0.9a entry point above retains its original identity contract.
    """
    if (sha(source), len(ledger['rows']), ledger['population'], ledger['pointer_bindings']) != (ledger['baseline_sha256'], 8038, 8038, 8946):
        raise ValueError('Exact reviewed intermediate/population required')
    rows=ledger['rows']
    if [r['id'] for r in rows]!=[f'D{i:05d}' for i in range(8038)]:raise ValueError('Incomplete or duplicate review')
    writes=[(w.identity,w.offset,w.expected,w.final) for w in inspection_writes]
    cursor=len(source);bindings=set();changed=0;records=[]
    for r in rows:
        if r['review']!='SOURCE_COMPARED':raise ValueError('Unreviewed text')
        pos=int(r['source_offset'],16);raw=read_c_string(source,pos,len(source))
        if sha(raw)!=r['source_sha256'] or b'\x12' in raw:raise ValueError('Source text mismatch '+r['id'])
        old=normalized(decode_game_text(source,raw));parts=[];end=0
        for a,b,replacement in r['spans']:
            if not 0<=end<=a<=b<=len(old):raise ValueError('Invalid authored span')
            parts.extend((old[end:a],replacement));end=b
        final=''.join(parts)+old[end:]
        if tokens(old)!=tokens(final):raise ValueError('Control changed '+r['id'])
        if numbers(old)!=numbers(final):
            if not (r['id'] in ('D00247','D07722') and r.get('numeral_notation') and numbers(old)==[] and numbers(final)==['１'] and '제１ 사냥터' in final):raise ValueError('Number changed '+r['id'])
        validate_layout(r['id'],[int(s,16) for s in r['bindings']],final)
        payload=encode_full(final)
        if normalized(decode_game_text(source,payload))!=final:raise ValueError('Glyph round trip '+r['id'])
        if not r['bindings']:raise ValueError('Unbound text')
        for s in r['bindings']:
            storage=int(s,16)
            if storage in bindings:raise ValueError('Duplicate pointer owner')
            bindings.add(storage)
            pointer=struct.unpack_from('<I',source,storage)[0]-0x08000000
            if not 0<=pointer<len(source) or read_c_string(source,pointer,len(source))!=raw:raise ValueError('Pointer changed '+r['id'])
            if r['spans']:writes.append((r['id']+'_ptr_'+s,storage,source[storage:storage+4],struct.pack('<I',cursor+0x08000000)))
        if r['spans']:
            if old==final:raise ValueError('Empty substantive change')
            writes.append((r['id']+'_text',cursor,b'\xff'*(len(payload)+1),payload+b'\0'))
            records.append(dict(id=r['id'],offset=cursor,sha256=sha(payload)))
            cursor+=len(payload)+1;changed+=1
    if len(bindings)!=8946 or changed!=ledger['changed']:raise ValueError('Coverage changed')
    glyphs=json.loads((ROOT/'config/private_glyph_order.json').read_text(encoding='utf-8'))['glyphs']
    index={c:i for i,c in enumerate(glyphs)}
    ui=json.loads((ROOT/'translation/v09a_ui_edits.json').read_text(encoding='utf-8'))
    for r in ui:
        storage=int(r['storage'],16);pointer=struct.unpack_from('<I',source,storage)[0]
        if storage in bindings or pointer!=int(r['source_pointer'],16):raise ValueError('UI binding conflict')
        raw=read_c_string(source,pointer-0x08000000,len(source))
        if sha(raw)!=r['source_sha256'] or r['id']!='SAVE_LOCATION_LABEL' or r['final']!='위치':raise ValueError('UI decision guard')
        payload=encode(r['final'],index)+b'\0'
        writes.append((r['id']+'_ptr',storage,source[storage:storage+4],struct.pack('<I',cursor+0x08000000)))
        writes.append((r['id']+'_text',cursor,b'\xff'*len(payload),payload));cursor+=len(payload)
    size=(cursor+0xffff)&~0xffff
    if size>0x02000000:raise ValueError('GBA ROM size limit')
    immutable=source+b'\xff'*(size-len(source));target=bytearray(immutable);end=0
    for key,pos,before,after in sorted(writes,key=lambda w:w[1]):
        if len(before)!=len(after) or pos<end or immutable[pos:pos+len(before)]!=before:raise ValueError('Writer/source conflict '+key)
        if any(pos<b and pos+len(after)>a for a,b in ((0xAC3F4,0xCB000),(0xCB000,0x2B2CAC))):raise ValueError('Protected asset write '+key)
        target[pos:pos+len(after)]=after;end=pos+len(after)
    return bytes(target),dict(reviewed=8038,bindings=len(bindings),changed=changed,size=size,sha256=sha(target),records=records)
