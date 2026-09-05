"""Individually reviewed FFR defects; never rewrite unrelated prose."""
import hashlib,json
from pathlib import Path
from extended_compact_spec import text_at
from confirmed_text_edits import encode_full
from narikiri2_text_spec import decode_game_text

def plans(source,root):
    rows=json.loads((root/'translation/reviewed_script_repairs.json').read_text(encoding='utf-8'))
    result=[]
    for row in rows:
        storage=int(row['storage'],16);pointer,raw=text_at(source,storage)
        if pointer!=int(row['source_pointer'],16) or hashlib.sha256(raw).hexdigest()!=row['source_sha256']:
            raise ValueError('Reviewed script repair source mismatch')
        final=bytes.fromhex(row['replacement_hex']) if 'replacement_hex' in row else raw
        for change in row.get('changes',[]):
            before,after=bytes.fromhex(change['before_hex']),bytes.fromhex(change['after_hex'])
            if final.count(before)!=1:raise ValueError('Repair occurrence is not unique')
            final=final.replace(before,after)
        decode_game_text(source,final)
        result.append(dict(id='SCRIPT_REPAIR_'+row['storage'],storage=storage,old_offset=pointer-0x08000000,payload=final))
    return result
