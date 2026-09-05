"""Decode the byte-oriented GBA type-30 run-length stream with strict bounds."""
def decompress(data,offset,maximum=0x20000,allow_padding=False):
    if offset+4>len(data) or data[offset]!=0x30:raise ValueError('Not a GBA RL stream')
    size=int.from_bytes(data[offset+1:offset+4],'little')
    if not 0<size<=maximum:raise ValueError('RL output size out of bounds')
    cursor=offset+4;out=bytearray()
    while len(out)<size:
        control=data[cursor];cursor+=1
        length=(control&127)+(3 if control&128 else 1)
        if len(out)+length>size+(3 if allow_padding else 0):
            raise ValueError(f'RL {offset:X}: run exceeds declared output and allowed padding')
        if control&128:
            out.extend(bytes((data[cursor],))*length);cursor+=1
        else:
            if cursor+length>len(data):raise ValueError('RL literal exceeds source')
            out.extend(data[cursor:cursor+length]);cursor+=length
    return bytes(out[:size]),cursor-offset
