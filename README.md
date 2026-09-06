# 나리키리 던전 2 — BETA3 기반 한국어 패치 v0.9b

FFR **BETA3(071102)**에 기존 v0.9a의 글꼴·이름·대사·표시 수정을 옮기고, 일본어 원문과 다시 대조해 번역을 보완한 **공개 검증판**입니다.

![프로젝트 식별 이미지](https://raw.githubusercontent.com/GimoXagros/narikiri2-save-compat/v0.9a/logo.png)

위 이미지는 사용자가 제출한 저장소 식별 이미지입니다. 공식 제휴를 뜻하지 않으며 이미지의 권리 경계는 [RIGHTS.md](RIGHTS.md)에 기록합니다. 배포 ZIP에 이미지 파일은 포함하지 않습니다.

## 적용

[v0.9b 릴리즈](https://github.com/GimoXagros/narikiri2-save-compat/releases/tag/v0.9b)의 `NARIKIRI2_AN9J_K_DALMOORI_v0.9b_BETA3_PACKAGE.zip`을 풀고 Python 3.10 이상으로 실행합니다. 적용에는 추가 패키지가 필요하지 않습니다.

```powershell
python apply_ffr_v09b.py "FFR_BETA3(071102).gba" --output "NARIKIRI2_AN9J_K_DALMOORI_v0.9b.gba"
```

**수정하지 않은 BETA3에 한 번만 적용합니다.** BETA2, 일본어판, v0.9/v0.9a나 이미 수정한 ROM은 입력으로 받지 않습니다. 원본과 기존 출력 파일은 덮어쓰지 않습니다.

| 파일 | 바이트 | SHA-256 |
| --- | ---: | --- |
| BETA3 입력 | 9,961,472 | `c6d7a401aa2a22362b2d27d0d31632cb2180a86b094788815d949b84c7fc944d` |
| v0.9b 결과 | 13,107,200 | `d761088a8549cb5bc60a2f03a4b78eea5282dbc17ed5da4ef1de27da4ad8d4d4` |
| BETA3 전용 BPS | 3,189,401 | `51dbdb8ef24a32ca5efb05ec3196b98ae08a32f3a4d6bb88673d58266837dcf6` |

## 반영한 내용

- v0.9a의 달무리 글꼴, 노란 배경 덧칠·전투 이름·적 정보창 수정을 BETA3에 이식했습니다.
- 기본 이름은 **훌리오 / 캐로**, 대사·도감의 명칭은 **필리아, 훈다크르, 나리키리사** 등으로 통일합니다. 별칭 **레이스**와 본명 **레이시스 포말하우트**는 문맥에 맞게 구별합니다.
- 대사·설명 등 실제 문자열 **8,037건**, 짧은 이름 필드 **1,227개**를 일본어와 개별 대조했습니다. BETA3에서 달라진 대사 2건을 반영하고, 추가로 문장 285건과 이름 필드 16개를 교정했습니다.
- 옷 교환 안내의 포인터 테이블을 문자열로 잘못 연결하던 부분을 복원했습니다. 이전 8,038건 집계 중 1건은 문자열이 아닌 이 테이블이었습니다.
- 새 게임 저장·재실행, 기존 8 KiB 저장, 혼합 이름, 중단 저장, 전투·적 정보창을 검증했습니다. 아이템·도감 일괄 표시와 기술 설명 231개도 확인했습니다.

일괄 표시에는 별도 RAM 시험 상태를 사용했습니다. 전체 게임 자연 해금·전편 플레이·실기 완료를 뜻하지 않습니다. 자세한 범위는 [VERIFICATION.md](VERIFICATION.md), 변경 예시는 [RELEASE_NOTES.md](RELEASE_NOTES.md)에 있습니다.

## 저장과 이전 버전

**BETA3에는 EEPROM 저장 코드가 이미 들어 있으므로 v0.5 저장 복구를 따로 적용할 필요가 없습니다.** v0.9b는 BETA3의 저장 코드를 그대로 유지합니다. BETA2의 저장 문제까지 사라진 것은 아닙니다. v0.5는 새 배포를 중단하고 이력·태그를 보존합니다. [배포 중단 이유와 지원 범위](docs/V05_RETIREMENT.md)를 확인하십시오.

시험한 기존 Candidate A/v0.9 계열 **8 KiB 게임 내 저장**은 이어하기와 재저장이 가능합니다. 원본 저장은 복사해 보관하고 실행기에 맞춰 새 ROM과 저장 파일의 기본 이름·위치를 맞추십시오. 사용자가 정한 이름은 유지되며 기본 이름 변경은 새 게임에 적용됩니다. 이전 ROM의 savestate나 출처를 판정하지 않은 32 KiB 저장은 이 도구의 변환 대상이 아닙니다.

## 공개 범위

공개 파일은 패치·도구·문서입니다. ROM, 세이브, BIOS, 전체 추출 대본은 포함하지 않습니다. [권리 고지](RIGHTS.md)와 [달무리 출처](THIRD_PARTY_NOTICES.md)를 확인하십시오.

v0.9b는 공개 검증판입니다. 최종 ROM의 실기·장시간 전체 진행은 [v1.0 검증 과제](https://github.com/GimoXagros/narikiri2-save-compat/issues/4)로 남아 있습니다.

[빌드 방법](BUILDING.md) · [BETA3 이식 기록](docs/BETA3_MIGRATION.md) · [v0.9a 역사 문서](docs/history/v0.9a/README.md) · [저장소 통합 기록](MIGRATION.md)
