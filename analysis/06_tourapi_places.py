"""가이드 웹용 장소 수집 — 한국관광공사 국문 관광정보 서비스_GW (TourAPI, data.go.kr 15101578, KorService2).

- 구장 좌표: searchKeyword2로 구장 자체를 찾아 TourAPI 좌표를 쓴다(못 찾으면 멈춤).
- 주변 장소: locationBasedList2 (거리순)
    관광지(12)·문화시설(14) 반경 5km / 음식점(39) 반경 3km / 숙박(32) 반경 10km (5km 안에 없는 구장이 있어서)
- 분류명: lclsSystmCode2 (신분류체계 전체 목록)
- 모든 응답은 data/raw/api/tourapi/에 캐시, 캐시가 있으면 다시 호출하지 않는다.
출력: data/processed/tour_places.csv, data/processed/tour_stadiums.csv
※ 이름·주소·좌표·분류만 쓴다. 영업시간·가격·이미지는 쓰지 않는다(CLAUDE.md §3-3, §3-6).
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "api" / "tourapi"
PROC = ROOT / "data" / "processed"
BASE = "https://apis.data.go.kr/B551011/KorService2/"

STADIUMS = [  # (KBO 구장명, TourAPI 검색어 후보, 결과 제목에 들어가야 할 문자열)
    ("잠실", ["잠실야구장"], "잠실"),
    ("고척", ["고척스카이돔", "고척 스카이돔", "고척돔"], "고척"),
    ("문학", ["랜더스필드", "문학야구장", "SSG랜더스"], "랜더스"),
    ("수원", ["위즈파크", "KT위즈"], "위즈"),
    ("대전", ["볼파크", "한화생명"], "볼파크"),
    ("대구", ["라이온즈파크", "삼성라이온즈"], "라이온즈"),
    ("광주", ["챔피언스필드", "기아챔피언스", "챔피언스 필드", "기아 챔피언스", "광주-기아"], "챔피언스"),
    ("사직", ["사직야구장"], "사직야구장"),
    ("창원", ["NC파크", "창원NC"], "NC"),
]
# TourAPI에서 구장을 못 찾을 때만 쓰는 좌표 (data/raw/kbo/stadiums.csv)
FALLBACK = ROOT / "data" / "raw" / "kbo" / "stadiums.csv"
TYPES = {12: ("관광지", 5000), 14: ("문화시설", 5000), 39: ("음식점", 3000), 32: ("숙박", 10000)}


def load_key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATA_GO_KR_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATA_GO_KR_KEY not found")


def call(key, op, cache_name, **params):
    path = RAW / f"{cache_name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    p = dict(serviceKey=key, MobileOS="ETC", MobileApp="kbo_tour", _type="json", pageNo=1, **params)
    r = requests.get(BASE + op, params=p, timeout=60)
    time.sleep(1.1)
    d = r.json()
    assert d["response"]["header"]["resultCode"] == "0000", r.text[:300]
    path.write_text(r.text, encoding="utf-8")
    return d


def items(d):
    it = d["response"]["body"].get("items")
    if not it:
        return []
    it = it["item"]
    return it if isinstance(it, list) else [it]


def main():
    key = load_key()
    cls = pd.DataFrame(items(call(key, "lclsSystmCode2", "lclsSystmCode2_all", numOfRows=1000, lclsSystmListYn="Y")))
    cls.to_csv(PROC / "tour_lclsSystm.csv", index=False, encoding="utf-8-sig")
    name3 = dict(zip(cls.get("lclsSystm3Cd", []), cls.get("lclsSystm3Nm", [])))

    st_rows, rows = [], []
    fb = pd.read_csv(FALLBACK).set_index("stadium")
    for stadium, kws, must in STADIUMS:
        s = None
        for kw in kws:
            cand = [i for i in items(call(key, "searchKeyword2", f"search_{kw}", numOfRows=20, keyword=kw, arrange="A"))
                    if must in i["title"] and i["contenttypeid"] == "28"]  # 28=레포츠(경기장)
            if cand:
                s = cand[0]
                break
        if s is not None:
            x, y = float(s["mapx"]), float(s["mapy"])
            st_rows.append(dict(stadium=stadium, title=s["title"], addr=s["addr1"], mapx=x, mapy=y,
                                contentid=s["contentid"], coord_source="TourAPI"))
        else:
            x, y = float(fb.loc[stadium, "lon"]), float(fb.loc[stadium, "lat"])
            s = {"contentid": None}
            st_rows.append(dict(stadium=stadium, title="", addr="", mapx=x, mapy=y, contentid=None,
                                coord_source="kbo-crowd stadiums.csv"))
        for ct, (label, radius) in TYPES.items():
            d = call(key, "locationBasedList2", f"loc_{stadium}_{ct}_{radius}", numOfRows=40, mapX=x, mapY=y,
                     radius=radius, arrange="E", contentTypeId=ct)
            for i in items(d):
                if i["contentid"] == s["contentid"]:
                    continue
                rows.append(dict(stadium=stadium, type=label, contenttypeid=ct, title=i["title"], addr=i.get("addr1", ""),
                                 dist_m=round(float(i.get("dist", 0))), mapx=float(i["mapx"]), mapy=float(i["mapy"]),
                                 cls3=i.get("lclsSystm3", ""), cls3_name=name3.get(i.get("lclsSystm3", ""), ""),
                                 contentid=i["contentid"], modifiedtime=i.get("modifiedtime", "")))
    pd.DataFrame(st_rows).to_csv(PROC / "tour_stadiums.csv", index=False, encoding="utf-8-sig")
    out = pd.DataFrame(rows)
    out.to_csv(PROC / "tour_places.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(st_rows).to_string())
    print(out.groupby(["stadium", "type"]).size().unstack())


if __name__ == "__main__":
    main()
