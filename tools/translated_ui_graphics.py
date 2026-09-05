"""Bounded text-region edits in identified UI graphics; source assets stay intact."""
from pathlib import Path
import struct
from find_gba_lz77_asset import decompress_lz77_stream
from narikiri2_item_ui_font import compress_lz77
from import_dalmoori_8x8 import generated_path,verify_checkout,parse_generated_glyph
from gba_rl import decompress as decompress_rl

def shop_stream(source,root):
    raw,consumed=decompress_lz77_stream(source,0x3A7C3C,0x20000)
    if len(raw)!=4096 or consumed!=2060 or source[0x3A7AE0:0x3A7AE4]!=struct.pack('<I',0x160):
        raise ValueError('SHOP graphics source profile changed')
    pixels=[[0]*256 for _ in range(32)]
    for y in range(32):
        for x in range(256):
            off=((y//8)*32+x//8)*32+(y%8)*4+(x%8)//2
            pixels[y][x]=(raw[off]>>(4*(x%2)))&15
    # This logo's palette explicitly uses 1/2/3 for purple edge and cyan ink;
    # 5/6/9/10 are its original background/border. Other atlas regions use other
    # palettes and are outside this writer's ownership.
    for y in range(24):
        for x in range(192,256):
            if pixels[y][x] in (1,2,3):pixels[y][x]=6
    checkout=root/'third_party/_work/dalmoori-font';verify_checkout(checkout)
    ink=set()
    for i,ch in enumerate('상점'):
        _,_,_,rows=parse_generated_glyph(generated_path(checkout,ch))
        bitmap=[[int(c=='#') for c in row] for row in rows]
        if len(bitmap[0])!=8:raise ValueError('SHOP title requires native full-width glyphs')
        for y,row in enumerate(bitmap):
            for x,value in enumerate(row):
                if value:ink.add((214+i*10+x,8+y))
    for x,y in ink:
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
            if (x+dx,y+dy) not in ink:pixels[y+dy][x+dx]=1
    for x,y in ink:pixels[y][x]=3
    final=bytearray(raw)
    for y in range(24):
        for x in range(192,256):
            off=((y//8)*32+x//8)*32+(y%8)*4+(x%8)//2
            shift=4*(x%2);final[off]=(final[off]&~(15<<shift))|(pixels[y][x]<<shift)
    allowed={((y//8)*32+x//8)*32+(y%8)*4+(x%8)//2 for y in range(24) for x in range(192,256)}
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(raw,final))):
        raise ValueError('SHOP translation changed another atlas region')
    compressed=compress_lz77(bytes(final),vram_safe=True)
    if len(compressed)>0x2000 or decompress_lz77_stream(compressed,0,0x20000)[0]!=final:
        raise ValueError('SHOP relocation capacity or roundtrip failure')
    return compressed

def plans(source,root):
    stream=shop_stream(source,root)
    info=info_stream(source,root)
    return [dict(id='shop_graphic_relative_pointer',category='pointer',offset=0x3A7AE0,
                 payload=struct.pack('<I',0xC1A000-0x3A7ADC),expected=struct.pack('<I',0x160)),
            dict(id='shop_graphic_native_dalmoori',category='graphics',offset=0xC1A000,
                 payload=stream,expected=b'\xff'*len(stream)),
            dict(id='info_graphic_relative_pointer',category='pointer',offset=0x380F20,
                 payload=struct.pack('<I',0xC1C000-0x380F08),expected=struct.pack('<I',0x13DC)),
            dict(id='info_graphic_native_dalmoori',category='graphics',offset=0xC1C000,
                 payload=info,expected=b'\xff'*len(info))]+title_plans(source,root)+battle_menu_plans(source,root)+battle_status_plans(source,root)+battle_result_plans(source,root)

def title_plans(source,root):
    """Four observed title prompts, preserving logo/copyright/cursor assets."""
    checkout=root/'third_party/_work/dalmoori-font';verify_checkout(checkout)
    result=[];base=0x3768F8
    # Runtime OAM proves left-to-right 32px pieces (final16px for suspend).
    # The game's allocator stores these pieces in reverse order.
    for ordinal,(index,offset,size,consumed,text,ink,edge) in enumerate((
        (10,0x37E370,512,374,'START 버튼',12,10),
        (13,0x37E6AC,512,246,'이어하기',1,9),
        (14,0x37E834,512,396,'처음부터',1,9),
        (15,0x37E9D4,640,530,'중단부터',1,9))):
        original,used=decompress_rl(source,offset,allow_padding=True)
        if len(original)!=size or used!=consumed:raise ValueError('Title graphics source profile changed')
        entry=base+4+index*4;expected=struct.pack('<I',offset-base)
        if source[entry:entry+4]!=expected:raise ValueError('Title relative owner changed')
        width=size//8;pieces=[]
        for ch in text:
            if ch==' ':pieces.append(['....']*8);continue
            _,_,_,rows=parse_generated_glyph(generated_path(checkout,ch))
            if len(rows)!=8 or len(rows[0]) not in (4,8):raise ValueError('Title glyph geometry changed')
            pieces.append(rows)
        text_width=sum(len(rows[0]) for rows in pieces)
        if text_width>width-2:raise ValueError('Title text overflow')
        x0=(width-text_width)//2;points=set()
        for rows in pieces:
            for y,row in enumerate(rows):
                for x,pixel in enumerate(row):
                    if pixel=='#':points.add((x0+x,4+y))
            x0+=len(rows[0])
        pixels=[[0]*width for _ in range(16)]
        for x,y in points:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<width and 0<=yy<16 and (xx,yy) not in points:pixels[yy][xx]=edge
        for x,y in points:pixels[y][x]=ink
        raw=bytearray()
        for left in reversed(range(0,width,32)):
            w=min(32,width-left)
            for ty in range(2):
                for tx in range(w//8):
                    for y in range(8):
                        for x in range(0,8,2):
                            xx=left+tx*8+x;yy=ty*8+y
                            raw.append(pixels[yy][xx]|pixels[yy][xx+1]<<4)
        if len(raw)!=size:raise ValueError('Title sprite piece packing changed')
        stream=compress_lz77(bytes(raw),vram_safe=True);target=0xC1E000+ordinal*0x200
        if len(stream)>0x200 or decompress_lz77_stream(stream,0,0x20000)[0]!=raw:
            raise ValueError('Title stream capacity/roundtrip failure')
        result.extend((dict(id=f'title_{index}_relative_pointer',category='pointer',offset=entry,
                            payload=struct.pack('<I',target-base),expected=expected),
                       dict(id=f'title_{index}_native_dalmoori',category='graphics',offset=target,
                            payload=stream,expected=b'\xff'*len(stream))))
    return result

def info_stream(source,root):
    original,consumed=decompress_rl(source,0x3822E4)
    if len(original)!=128 or consumed!=88:
        raise ValueError('INFO sprite source profile changed')
    checkout=root/'third_party/_work/dalmoori-font';verify_checkout(checkout)
    ink=set()
    for i,ch in enumerate('정보'):
        _,_,_,rows=parse_generated_glyph(generated_path(checkout,ch))
        if len(rows)!=8 or any(len(row)!=8 for row in rows):raise ValueError('INFO native glyph geometry changed')
        for y,row in enumerate(rows):
            for x,pixel in enumerate(row):
                if pixel=='#':ink.add((1+i*9+x,y))
    pixels=[[0]*32 for _ in range(8)]
    for x,y in ink:
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
            xx,yy=x+dx,y+dy
            if 0<=xx<32 and 0<=yy<8 and (xx,yy) not in ink:pixels[yy][xx]=8
    for x,y in ink:pixels[y][x]=5
    raw=bytearray(128)
    for y in range(8):
        for x in range(32):raw[(x//8)*32+y*4+(x%8)//2]|=pixels[y][x]<<(4*(x%2))
    stream=compress_lz77(bytes(raw),vram_safe=True)
    if len(stream)>0x2000 or decompress_lz77_stream(stream,0,0x20000)[0]!=raw:
        raise ValueError('INFO sprite compression failure')
    return stream


def battle_menu_plans(source,root):
    """Four action labels; original icon, background, palette, OAM geometry stay intact."""
    import hashlib
    from build_dalmoori_gba_font import pack_4bpp
    base=0x6D7CBC
    if hashlib.sha256(source[base:base+0x700]).hexdigest()!='c3e3a41509853013f6711c9de170ad606b9392716e30763dd7836779c88bcb7c':
        raise ValueError('Battle menu atlas profile changed')
    checkout=root/'third_party/_work/dalmoori-font';verify_checkout(checkout)
    result=[]
    # Sprite frames6..17 contain one8x8 tile, atlas indices44..55.
    for sprite,ch in ((6,'작'),(7,'기'),(8,'전'),(10,'특'),(12,'도'),(13,'구'),(14,'대'),(15,'열')):
        frame=0x3AFE6C+(sprite-6)*12
        expected=struct.pack('<3I',1,0x02000000,sprite+38)
        if source[frame:frame+12]!=expected:raise ValueError('Battle label frame binding changed')
        _,_,_,rows=parse_generated_glyph(generated_path(checkout,ch))
        if len(rows)!=8 or any(len(row)!=8 for row in rows):raise ValueError('Battle label native glyph geometry')
        raw=pack_4bpp([[int(c=='#') for c in row] for row in rows],0,15)
        offset=base+(sprite+38)*32
        result.append(dict(id=f'battle_menu_glyph_{sprite}',category='graphics',offset=offset,payload=raw,expected=source[offset:offset+32]))
    original_rows=[
      '0a000000070800000d1000000b15fe0005feff000506ff00050eff0000000000',
      '0600000007080000081000000918000005feff000506ff00050eff000516ff00',
      '0a0000000b06fe000c0c0000071500000b1bfe0005feff00050aff000513ff00',
      '0e0000000f080000101000001118000005feff000506ff00050eff000516ff00']
    for n,(word,sprites) in enumerate((('특기',(10,7)),('작전',(6,8)),('도구',(12,13)),('대열',(14,15)))):
        raw=struct.pack('<4b',sprites[0],4,0,0)+struct.pack('<4b',sprites[1],12,0,0)
        raw+=struct.pack('<4b',5,2,-1,0)+struct.pack('<4b',5,10,-1,0)+bytes(16)
        result.append(dict(id=f'battle_menu_label_{n}',category='graphics_layout',offset=0x3AFF88+n*32,
                           payload=raw,expected=bytes.fromhex(original_rows[n])))
    return result


def battle_status_plans(source,root):
    """PAUSE and TARGET in battle atlas0; damage digits, arrows, dashes stay intact."""
    import hashlib
    if hashlib.sha256(source[0x6D587C:0x6D6C3C]).hexdigest()!='bc3b4fc69ec380720fce36d9125bad5d21a1031ddfa858ee81898e35d7dd3c0f':
        raise ValueError('Battle status atlas profile changed')
    checkout=root/'third_party/_work/dalmoori-font';verify_checkout(checkout)
    result=[]
    for identity,offset,width,height,word in (('pause',0x6D60BC,40,16,'일시정지'),('target',0x6D63BC,40,8,'표적')):
        points=set();x0=(width-len(word)*8)//2;y0=(height-8)//2
        for i,ch in enumerate(word):
            _,_,_,rows=parse_generated_glyph(generated_path(checkout,ch))
            if len(rows)!=8 or any(len(row)!=8 for row in rows):raise ValueError('Battle status native glyph geometry')
            points.update((x0+i*8+x,y0+y) for y,row in enumerate(rows) for x,c in enumerate(row) if c=='#')
        pixels=[[0]*width for _ in range(height)]
        for x,y in points:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<width and 0<=yy<height and (xx,yy) not in points:pixels[yy][xx]=5
        for x,y in points:pixels[y][x]=15
        raw=bytearray()
        for left in range(0,width,32):
            for ty in range(height//8):
                for tx in range(min(32,width-left)//8):
                    for y in range(8):
                        for x in range(0,8,2):
                            xx=left+tx*8+x;yy=ty*8+y
                            raw.append(pixels[yy][xx]|pixels[yy][xx+1]<<4)
        if len(raw)!=width*height//2:raise ValueError('Battle status packing bound')
        result.append(dict(id=f'battle_{identity}_graphic',category='graphics',offset=offset,payload=bytes(raw),expected=source[offset:offset+len(raw)]))
    return result


def battle_result_plans(source,root):
    """All eight word frames in the result atlas; the ten numeral frames are preserved."""
    import hashlib
    base=0x6D6C3C
    if hashlib.sha256(source[base:0x6D7B7C]).hexdigest()!='a72e6875dee678b86d0bf88be1400e614e881ebd591cd33238ec012e2473f461':raise ValueError('Battle result atlas profile changed')
    checkout=root/'third_party/_work/dalmoori-font';verify_checkout(checkout)
    result=[]
    profiles=[('bonus',0,48,'보너스',False),('gald',12,40,'갈드',True),('exp',22,32,'경험치',False),
              ('level',30,32,'레벨',False),('level_up',38,24,'상승',False),('hit',100,32,'연타',False),
              ('skill',108,32,'기술',False),('skill_up',116,24,'상승',False)]
    for identity,tile,width,word,reverse in profiles:
        points=set();x0=(width-len(word)*8)//2
        for i,ch in enumerate(word):
            _,_,_,rows=parse_generated_glyph(generated_path(checkout,ch))
            if len(rows)!=8 or any(len(row)!=8 for row in rows):raise ValueError('Battle result glyph geometry')
            points.update((x0+i*8+x,4+y) for y,row in enumerate(rows) for x,c in enumerate(row) if c=='#')
        pixels=[[0]*width for _ in range(16)]
        for x,y in points:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<width and 0<=yy<16 and (xx,yy) not in points:pixels[yy][xx]=2
        for x,y in points:pixels[y][x]=15
        raw=bytearray();pieces=[(0,32),(32,width-32)] if width>32 else ([(0,16),(16,8)] if width==24 else [(0,width)])
        if reverse:pieces.reverse()
        for left,w in pieces:
            for ty in range(2):
                for tx in range(w//8):
                    for y in range(8):
                        for x in range(0,8,2):
                            xx=left+tx*8+x;yy=ty*8+y;raw.append(pixels[yy][xx]|pixels[yy][xx+1]<<4)
        offset=base+tile*32
        if len(raw)!=width*8:raise ValueError('Battle result packing bound')
        result.append(dict(id=f'battle_result_{identity}',category='graphics',offset=offset,payload=bytes(raw),expected=source[offset:offset+len(raw)]))
    return result
