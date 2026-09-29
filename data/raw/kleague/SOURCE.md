# K리그1 경기·경기장 원자료 (확장 검증용)

- 출처: 한국어 위키백과(https://ko.wikipedia.org). MediaWiki API로 문서 원문(wikitext)만 받았다(`analysis/14_fetch_kleague.py`, 요청 간 1.2초).
- 라이선스: **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/deed.ko). 이 폴더의 `*.wikitext`는 위키백과 기여자들의 저작물이며 같은 라이선스를 따른다.
- 판 번호·영구 링크: 각 `*.meta.json`의 `revid`, `permalink` (경기장 문서는 `stadium_articles/_meta.json`)
  - 2024년 K리그1의 경기 결과: https://ko.wikipedia.org/w/index.php?oldid=41076393
  - 2025년 K리그1의 경기 결과: https://ko.wikipedia.org/w/index.php?oldid=41076398
  - 2024년 K리그1: https://ko.wikipedia.org/w/index.php?oldid=41807274
  - 2025년 K리그1: https://ko.wikipedia.org/w/index.php?oldid=42158664
- 쓰임: 경기별 날짜·시간·경기장·홈/원정·관중 수(`data/processed/kleague_matches.csv`), 경기장 주소 → 시군구(`data/processed/kleague_stadium_region.csv`)
- 검증: 2025 정규 33라운드 종료(10/18) 누적 관중 경기별 합계 2,047,370명 vs 한국프로축구연맹 발표 2,047,564명(−0.01%, https://sports.news.nate.com/view/20251018n11850)
- K리그 공식 사이트(kleague.com)의 데이터는 수집하지 않았다.
