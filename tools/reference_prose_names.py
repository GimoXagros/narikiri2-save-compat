"""Apply approved proper-name spellings in individually bound full-text records.

Only name bytes change. Controls, punctuation, all other prose and the original
record remain intact. Source-language entity evidence excludes substring traps
such as 조니 inside 이류조니스토 (イリュージョニスト).
"""
import csv
import hashlib
import json
from pathlib import Path
import unicodedata
from confirmed_text_edits import encode_full
from extended_compact_spec import text_at
from narikiri2_text_spec import decode_game_text

ROOT=Path(__file__).resolve().parents[1]
RULES=(('프리오','훌리오','フリオ'),('흐리오','훌리오','フリオ'),
       ('캬로','캐로','キャロ'),('크라스','클라스','クラース'),
       ('조니','죠니','ジョニー'),('멜디','메르디','メルディ'),
       ('챗','채트','チャット'),('챠트','채트','チャット'),
       ('릴리스','리리스','リリス'),('발키리','왈큐레','ワルキューレ'),
       ('스턴','스탄','スタン'),('릿드','리드','リッド'),
       ('피리아','필리아','フィリア'),('화라','파라','ファラ'))

BIO_NAMES={0:'크레스 알베인',1:'체스터 버클라이트',2:'민트 아드네이드',
           3:'클라스 F. 레스터',4:'아체 클라인',5:'후지바야시 스즈',
           6:'스탄 엘론',7:'루티 카틀릿',8:'리온 매그너스',9:'필리아 필리스',
           10:'우드로우 켈빈',11:'첼시 톤',12:'마리 에이젠트',13:'마이티 콩맨',
           14:'죠니 시덴',15:'리드 허셸',16:'파라 엘스테드',17:'킬 차이벨'}

def plans(source,root=ROOT):
    entries=json.loads((root/'translation/reference_prose_name_edits.json').read_text(encoding='utf-8'))
    result=[]
    for row in entries:
        storage=int(row['storage'],16); pointer,raw=text_at(source,storage)
        if pointer!=int(row['source_pointer'],16) or hashlib.sha256(raw).hexdigest()!=row['source_sha256']:
            raise ValueError('Reference prose source binding mismatch')
        payload=raw
        for change in row['changes']:
            before,after=encode_full(change['before']),encode_full(change['after'])
            if payload.count(before)!=change['occurrences']:
                raise ValueError('Reference prose exact occurrence mismatch')
            payload=payload.replace(before,after)
        # Decode equality independently rejects replacements cutting a multibyte
        # glyph. Re-encoding the whole script would risk changing its controls.
        expected=decode_game_text(source,raw)
        for c in row['changes']:expected=expected.replace(c['before'],c['after'])
        if decode_game_text(source,payload)!=expected:
            raise ValueError('Reference prose glyph boundary mismatch')
        result.append(dict(id=f'REFERENCE_NAME_{storage:08X}',storage=storage,
                           old_offset=pointer-0x08000000,payload=payload))
    return result

def adopt():
    source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
    with (ROOT/'translation/banked_full_names.tsv').open(encoding='utf-8-sig',newline='') as f:
        owned={int(r['storage'],16) for r in csv.DictReader(f,delimiter='\t')}
    with (ROOT/'analysis/expanded_pointer_survey.csv').open(encoding='utf-8',newline='') as f:
        candidates=list(csv.DictReader(f))
    entries=[]; private=[]
    for row in candidates:
        storage=int(row['storage_hex'],16)
        if storage in owned:continue
        jp=unicodedata.normalize('NFKC',row['jp_decode_hypothesis'])
        old=row['kr_decode_hypothesis']; changes=[]
        bio_index=(storage-0x2C5338)//40
        if storage==0x2C5338+bio_index*40 and bio_index in BIO_NAMES:
            before=old.split('\u3000')[0]
            after=BIO_NAMES[bio_index].replace(' ','\u3000').replace('F.','Ｆ．')
            if len(after)>14:raise ValueError('Character biography name envelope exceeded')
            changes.append(dict(before=before,after=after,japanese_entity=jp.split(' ')[0],occurrences=1))
        else:
            for before,after,entity in RULES:
                if before in old and entity in jp:
                    changes.append(dict(before=before,after=after,japanese_entity=entity,occurrences=old.count(before)))
        if not changes:continue
        pointer,raw=text_at(source,storage)
        if raw.hex().upper()!=row['kr_raw_hex'] or decode_game_text(source,raw)!=old:
            raise ValueError('Candidate source interpretation mismatch')
        entries.append(dict(storage=f'{storage:08X}',source_pointer=f'{pointer:08X}',
                            source_sha256=hashlib.sha256(raw).hexdigest(),changes=changes))
        after=old
        for c in changes:after=after.replace(c['before'],c['after'])
        private.append(dict(storage=f'{storage:08X}',japanese=jp,before=old,after=after,
                            status='USER_APPROVED_NAME_NORMALIZATION_RUNTIME_PENDING'))
    (ROOT/'translation/reference_prose_name_edits.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'analysis/private/reference_prose_name_review.json').write_text(json.dumps(private,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    checked=plans(source)
    print(json.dumps(dict(records=len(checked),name_occurrences=sum(c['occurrences'] for e in entries for c in e['changes']),payload_bytes=sum(len(e['payload'])+1 for e in checked)),ensure_ascii=False))

if __name__=='__main__':adopt()
