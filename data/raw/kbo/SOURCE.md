# KBO 경기·관중 원자료 출처

## 파일
| 파일 | 내용 |
|---|---|
| games.csv | 경기별 날짜·요일·홈·원정·구장·관중 수 (2021~2026-09-27, 정규시즌) |
| schedule.csv | 편성 전체(취소 포함): 시작시각, 스코어, 비고(우천취소·그라운드사정·폭염취소·미세먼지취소·기타) |
| stadiums.csv | 구장 목록(수용인원 추정, 좌표) — 참고용, 분석은 data/processed/stadium_region.csv 사용 |
| holidays.csv | 공휴일·대체·임시공휴일·선거일 (수기 관리 목록) |

## 경로
- 원출처: KBO 기록실 [일자별 관중 현황](https://www.koreabaseball.com/Record/Crowd/GraphDaily.aspx), KBO 일정 페이지
- 취득 경로: 공개 GitHub 저장소 [KENNYSOFT/kbo-crowd](https://github.com/KENNYSOFT/kbo-crowd) `data/*.csv` (main 브랜치, 2026-09-29 KST 01:55 내려받음)
  - 이 저장소는 KBO 기록실 원자료를 매일 다시 받아 CSV로 올린다(README 기준). **라이선스 표기 없음.**
- 직접 수집하지 않은 이유: koreabaseball.com의 robots.txt가 `User-agent: * / Disallow: /`이고,
  "본 사이트의 데이터를 사전 승인 없이 자동 수집·크롤링·복제하는 행위를 금지합니다"라고 명시 (2026-09-29 확인).
- 대안 검토: 한국프로스포츠협회 data.prosports.or.kr → "서비스 개편 중"(2026-09-29). mykbostats.com → 봇 차단(Cloudflare) 페이지라 사용 안 함.

## 검증 (시즌 총관중, games.csv 합계 vs 공식 발표)
| 시즌 | games.csv 합계 | 공식 발표 | 출처 |
|---|---|---|---|
| 2023 | 8,100,326 | 810만 326명 | [스포츠타임스](http://www.thesportstimes.co.kr/news/articleView.html?idxno=344453), [엑스포츠뉴스](https://www.xportsnews.com/article/2129170) |
| 2024 | 10,887,705 | 1,088만 7,705명 | [MK스포츠](https://www.mksports.co.kr/news/sports/11129640) |
| 2025 | 12,312,519 | 1,231만 2,519명 | [엑스포츠뉴스](https://www.xportsnews.com/article/2129170) |

세 시즌 모두 1명 단위까지 일치. 각 시즌 720경기.

## 남은 확인 (사용자)
- 최종 제출 전 KBO 기록실 화면에서 임의의 경기일 3~5개를 눈으로 대조(관중·구장) → 일치하면 서식4 출처를 "KBO 기록실 경기별 관중 현황"으로 표기.
