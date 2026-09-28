"""한국관광공사_빅데이터_지역별 방문자수_GW (data.go.kr 15101972) 수집.

- 기초(locgoRegnVisitrDDList): 월 단위 1회 호출 (월 ~24,500행)
- 광역(metcoRegnVisitrDDList): 분기 단위 1회 호출
- 모든 응답은 data/raw/api/{endpoint}/ 에 캐시하고, 캐시가 있으면 다시 호출하지 않는다.
- 결과: data/processed/visitors_sigungu_daily.parquet, visitors_sido_daily.parquet

실행: python analysis/01_collect_visitors.py
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "api"
PROC = ROOT / "data" / "processed"
BASE = "https://apis.data.go.kr/B551011/DataLabService/"

START = date(2023, 1, 1)
END = date(2026, 8, 29)  # API 제공 최신일 (2026-09-29 확인)


def load_key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATA_GO_KR_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATA_GO_KR_KEY not found in .env")


def month_ranges(start, end):
    cur = start.replace(day=1)
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield max(cur, start), min(nxt - timedelta(days=1), end)
        cur = nxt


def quarter_ranges(start, end):
    cur = start.replace(day=1)
    while cur <= end:
        m = cur.month + 3
        nxt = date(cur.year + (m - 1) // 12, (m - 1) % 12 + 1, 1)
        yield max(cur, start), min(nxt - timedelta(days=1), end)
        cur = nxt


def fetch(key, endpoint, s, e, calls):
    out = RAW / endpoint / f"{s:%Y%m%d}_{e:%Y%m%d}.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    params = dict(serviceKey=key, MobileOS="ETC", MobileApp="kbo_tour", _type="json",
                  numOfRows=50000, pageNo=1, startYmd=f"{s:%Y%m%d}", endYmd=f"{e:%Y%m%d}")
    for attempt in range(3):
        r = requests.get(BASE + endpoint, params=params, timeout=300)
        calls.append(1)
        time.sleep(1.1)
        try:
            d = r.json()
            body = d["response"]["body"]
            n_items = len(body["items"]["item"]) if body.get("items") else 0
            assert n_items == body["totalCount"], (n_items, body["totalCount"])
            out.write_text(r.text, encoding="utf-8")
            return d
        except Exception as ex:  # noqa: BLE001
            print("  retry", endpoint, s, e, ex, r.text[:200])
            time.sleep(5)
    raise RuntimeError(f"failed {endpoint} {s} {e}")


def to_frame(d):
    body = d["response"]["body"]
    return pd.DataFrame(body["items"]["item"]) if body.get("items") else pd.DataFrame()


def main():
    key = load_key()
    calls = []
    frames = []
    for s, e in month_ranges(START, END):
        frames.append(to_frame(fetch(key, "locgoRegnVisitrDDList", s, e, calls)))
        print("locgo", s, e, len(frames[-1]))
    loc = pd.concat(frames, ignore_index=True)

    frames = []
    for s, e in quarter_ranges(START, END):
        frames.append(to_frame(fetch(key, "metcoRegnVisitrDDList", s, e, calls)))
        print("metco", s, e, len(frames[-1]))
    met = pd.concat(frames, ignore_index=True)
    print("API calls this run:", len(calls))

    PROC.mkdir(parents=True, exist_ok=True)
    div = {"1": "local", "2": "outsider", "3": "foreigner"}

    loc["date"] = pd.to_datetime(loc["baseYmd"])
    loc["touNum"] = loc["touNum"].astype(float)
    loc["div"] = loc["touDivCd"].map(div)
    w = (loc.pivot_table(index=["signguCode", "signguNm", "date"], columns="div",
                         values="touNum", aggfunc="sum").reset_index())
    w.columns.name = None
    w.to_parquet(PROC / "visitors_sigungu_daily.parquet", index=False)

    code_col = [c for c in met.columns if c.lower().endswith("code")][0]
    name_col = [c for c in met.columns if c.lower().endswith("nm") and "Div" not in c and "daywk" not in c][0]
    met["date"] = pd.to_datetime(met["baseYmd"])
    met["touNum"] = met["touNum"].astype(float)
    met["div"] = met["touDivCd"].map(div)
    m = (met.pivot_table(index=[code_col, name_col, "date"], columns="div",
                         values="touNum", aggfunc="sum").reset_index()
         .rename(columns={code_col: "sidoCode", name_col: "sidoNm"}))
    m.columns.name = None
    m.to_parquet(PROC / "visitors_sido_daily.parquet", index=False)
    print("sigungu rows", len(w), "codes", w.signguCode.nunique(), w.date.min(), w.date.max())
    print("sido rows", len(m), "codes", m.sidoCode.nunique())


if __name__ == "__main__":
    main()
