"""Source-bound display labels; keyboard input lookup arrays are untouched."""
from extended_compact_spec import text_at

# Three six-row display tables are consumed by 08019EF4. Input selection
# instead uses 083A7A5C/60 through 08019FC8/1A068/1A118.
LABELS = (
    (0x3A7A78, 0x2C77BC, b'OK', '결정'),
    (0x3A7A74, 0x2C77E4, b'BACK', '지우기'),
    (0x3A7A70, 0x2C7810, b'CHANGE', '전환'),
    (0x3A7A90, 0x2C7868, b'OK', '결정'),
    (0x3A7A8C, 0x2C788C, b'BACK', '지우기'),
    (0x3A7A88, 0x2C78B8, b'CHAN', '전환'),
    (0x3A7AA8, 0x2C791C, b'OK', '결정'),
    (0x3A7AA4, 0x2C7938, b'BACK', '지우기'),
    (0x3A7AA0, 0x2C7954, b'CHANGE', '전환'),
    (0xED40, 0x2C3890, b'NO ENTRY', '동료 없음'),
    (0xEFB4, 0x2C3890, b'NO ENTRY', '동료 없음'),
)

def plans(source, encode):
    result=[]
    for storage,offset,old,new in LABELS:
        pointer,raw=text_at(source,storage)
        if pointer!=0x08000000+offset or raw.count(old)!=1:
            raise ValueError('Fixed display label source identity changed')
        before,after=raw.split(old)
        if after not in (b'', b'\n') or len(new)>len(old):
            raise ValueError('Fixed display label column or suffix changed')
        payload=before+encode(new)+after
        if len(payload)>64: raise ValueError('Fixed display row bound exceeded')
        result.append(dict(id=f'FIXED_UI_{storage:08X}',storage=storage,
                           old_offset=offset,payload=payload))
    return result
