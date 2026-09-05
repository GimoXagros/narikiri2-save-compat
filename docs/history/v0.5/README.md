# 나리키리 던전 2 — 실기 저장 호환 복구 도구 v0.5

**한글패치가 아닌, 기존 K_FFR 한글판의 저장 호환성을 복원하는 로컬 도구입니다.**

사용자가 보유한 최초 K_FFR 한글판과 정확히 일치하는 일본어 원본에서 저장 관련 구간을 읽어 새 ROM을 만듭니다. 도구 자체에는 게임의 실행 코드 바이트, 번역문, 폰트, ROM, 세이브, BPS/IPS 패치가 없습니다. 다운로드·업로드 기능이나 외부 라이브러리 의존성도 없습니다.

복구 결과는 기존 v0.5 / Candidate A와 같습니다. 12 MiB 크기를 유지하고 저장 관련 79바이트만 달라집니다. 영어 아이템명, 기존 번역과 글꼴은 변경하지 않습니다.

## 준비물

- Python 3.10 이상. 별도 Python 패키지는 필요하지 않습니다.
- 아래 SHA-256과 일치하는 두 입력 ROM. 이 저장소는 게임이나 기존 한글패치를 제공하거나 구하는 방법을 안내하지 않습니다.
- 원본 ROM과 기존 세이브의 별도 백업.

| 파일 역할 | 크기 | SHA-256 |
| --- | ---: | --- |
| 최초 K_FFR 한글판 | 12,582,912 | `f94cb5a128c8a98e6e18e6a0598ebf9b266f54da0750367af8defac3eb2df7d4` |
| 일본어 원본 | 8,388,608 | `a92c0f6dbb5c013b47b7178e23d81663e3952a10df7b1f68967ebf7bb3b98eb7` |
| 복구 결과 | 12,582,912 | `9c7a8ae87c303a16c71bd164e7409a5aaabf01bd3246fa9e700931eed6179d4f` |

파일명이 아니라 크기와 SHA-256을 검사합니다. 다른 리비전, 추가 번역 개발본, 이미 복구한 ROM은 입력으로 허용하지 않습니다. 결과 해시가 이미 위와 같다면 다시 복구할 필요가 없습니다.

## 사용법

릴리즈의 `NARIKIRI2_SAVE_COMPAT_v0.5_SOURCE_ONLY.zip`을 풀고, 해당 폴더에서 다음 명령의 파일 경로를 바꿔 실행합니다.

```powershell
python restore.py --korean "최초_K_FFR.gba" --japanese "일본어_원본.gba" --output "NARIKIRI2_SAVE_COMPAT_v0.5.gba"
```

출력은 **아직 없는 새 .gba 파일**이어야 합니다. 출력 폴더는 미리 만들어 두십시오. 입력·출력 검증 실패 시 성공으로 표시하지 않으며, 기존 파일 덮어쓰기를 허용하는 옵션은 없습니다. 저장 공간 부족 등 쓰기 오류가 발생하면 새 출력이 불완전하게 남을 수 있으므로 사용하지 마십시오. 두 입력은 읽기 전용으로 취급합니다.

## 세이브와 사용 환경

도구는 .sav 파일을 읽거나 변경하지 않습니다. 검증된 Candidate A의 8 KiB 세이브는 동일한 결과 ROM에서 계속 사용할 수 있습니다. ROM과 세이브의 기본 파일명 및 저장 위치는 사용하는 실행기의 규칙에 맞추십시오. 기존 savestate/자동 이어하기 대신 완전히 종료한 뒤 게임의 Continue로 불러오는 것을 권장합니다.

수정 전 VBA-M에서 생성한 32 KiB 세이브는 그대로 호환된다고 가정하지 마십시오. 형식 확인 및 별도 변환이 필요할 수 있으며 이 공개 도구는 세이브 변환을 하지 않습니다. 유일한 세이브 사본에 시험하지 마십시오.

저장 복원은 최초 한글판의 SRAM 접근 변경을 원래 EEPROM 경로로 돌리는 것입니다. 이 도구가 모든 플래시카트나 실행기의 문제를 해결하는 것은 아닙니다. 기존 게임의 번역·오탈자·진행 버그를 수정하지 않습니다.

## 검증 및 한계

최종 출력과 기존 검증본의 전체 바이트 동일성으로 기존 저장·로드 관찰을 연결합니다. 기존 v0.5에서는 mGBA libretro로 새 게임 최초 저장 → 재실행·로드 → 추가 진행·두 번째 저장 → 재실행·로드를 확인했습니다. GBARunner3에서는 사용자가 같은 Candidate A ROM의 저장·로드 성공을 보고했습니다. 이는 새 도구로 모든 실기 환경을 다시 시험했다는 뜻이 아닙니다.

[검증 기록](VERIFICATION.md)과 [배포 권리 검토](RIGHTS.md)를 확인하십시오. 전편 플레이나 모든 하드웨어의 무결함은 보장하지 않습니다.

```powershell
python -m unittest discover -s tests -v
```

위 테스트는 합성 데이터만 사용하므로 게임 파일 없이 실행할 수 있습니다. 실제 ROM 검증 방법은 VERIFICATION.md에 있습니다.

## 라이선스와 기여

새로 작성한 도구 코드·테스트·문서는 [MIT 라이선스](LICENSE)로 공개합니다. 원 게임, 기존 한글패치, 입력 ROM과 생성 ROM의 제3자 자료에는 이 라이선스가 적용되지 않습니다. 해당 권리는 각 권리자에게 있습니다. 공식 제품이나 권리자의 승인을 받은 프로젝트라는 의미가 아닙니다.

이슈와 PR에 ROM, 세이브, 추출 번역문, 폰트, 게임 코드 덤프 또는 이를 포함한 패치를 올리지 마십시오. 오류 메시지·파일 크기·SHA-256 및 개인정보를 제거한 재현 절차만 공유하십시오.

## English summary

Local-only save compatibility restoration, not a translation patch. Supply the exact original K_FFR and Japanese ROMs yourself. The tool embeds no game instructions/assets and performs no network access. It restores three donor ranges at their original offsets and verifies the complete output; exactly 79 bytes change. Existing files are never overwritten. MIT covers only this project's authored software/documentation, not the game or existing translation. No ROMs, saves, binary patches, or extracted game assets are accepted in contributions.
