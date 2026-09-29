"""확장 분석(K리그1) 원자료 수집 — 한국어 위키백과 공식 API(MediaWiki API)로 문서 원문(wikitext)만 받는다.

- 경기: '2024년 K리그1의 경기 결과', '2025년 K리그1의 경기 결과' (날짜·시간·경기장·홈팀·원정팀·관중 수)
- 경기장 주소: 각 경기장 문서의 정보상자 '위치' (경기장 → 시군구 매핑 근거)
- 교차 확인용: '2024년 K리그1', '2025년 K리그1' 시즌 문서(구단별 관중 표)
- 라이선스: CC BY-SA 4.0. 문서 판 번호(revid)를 함께 저장해 인용·재현이 가능하게 한다.
- 이미 받은 파일은 다시 받지 않는다(요청 간 1.2초, User-Agent 명시).
"""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "kleague"
ART = RAW / "stadium_articles"
API = "https://ko.wikipedia.org/w/api.php"
UA = {"User-Agent": "jikgwan-guide-research/0.1 (personal non-commercial analysis; https://github.com/lethargic21/jikgwan-guide)"}

MATCH_PAGES = ["2024년 K리그1의 경기 결과", "2025년 K리그1의 경기 결과"]
SEASON_PAGES = ["2024년 K리그1", "2025년 K리그1"]
VENUES = ["인천축구전용구장", "대전월드컵경기장", "김천종합운동장", "광주축구전용구장", "DGB대구은행파크", "울산문수축구경기장",
          "서울월드컵경기장", "수원종합운동장", "전주월드컵경기장", "포항 스틸야드", "제주월드컵경기장", "강릉종합운동장",
          "춘천송암스포츠타운", "울산종합운동장", "광주월드컵경기장", "안양종합운동장"]


def fetch(title):
    r = requests.get(API, params=dict(action="query", prop="revisions", titles=title, rvprop="content|ids|timestamp",
                                      rvslots="main", redirects=1, format="json"), headers=UA, timeout=30)
    time.sleep(1.2)
    pg = next(iter(r.json()["query"]["pages"].values()))
    rev = pg["revisions"][0]
    meta = dict(title=pg["title"], pageid=pg["pageid"], revid=rev["revid"], timestamp=rev["timestamp"],
                url="https://ko.wikipedia.org/wiki/" + pg["title"].replace(" ", "_"),
                permalink=f"https://ko.wikipedia.org/w/index.php?oldid={rev['revid']}", license="CC BY-SA 4.0")
    return rev["slots"]["main"]["*"], meta


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    for title in MATCH_PAGES + SEASON_PAGES:
        fn = RAW / f"wiki_{title.replace(' ', '_')}.wikitext"
        if fn.exists():
            continue
        txt, meta = fetch(title)
        fn.write_text(txt, encoding="utf-8")
        (RAW / (fn.stem + ".meta.json")).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print("받음", title, meta["revid"])
    mfile = ART / "_meta.json"
    meta_all = json.loads(mfile.read_text(encoding="utf-8")) if mfile.exists() else {}
    for v in VENUES:
        fn = ART / f"{v}.wikitext"
        if fn.exists() and v in meta_all and "permalink" in meta_all[v]:
            continue
        txt, meta = fetch(v)
        fn.write_text(txt, encoding="utf-8")
        meta_all[v] = meta
        print("받음", v, "→", meta["title"])
    mfile.write_text(json.dumps(meta_all, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
