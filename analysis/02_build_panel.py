"""분석용 패널 구축: 시군구 × 일 외지인 방문자 + 홈경기 처치변수.

입력
- data/processed/visitors_sigungu_daily.parquet (01_collect_visitors.py)
- data/raw/kbo/games.csv, schedule.csv, holidays.csv (KBO 기록실 원자료, SOURCE.md 참조)
- data/processed/stadium_region.csv

출력
- data/processed/panel_sigungu_daily.parquet : 균형 패널(최하위 단위), 광역 코드 포함
- data/processed/kbo_games_clean.csv        : 경기별(구장→시군구 코드 부착)
- data/processed/stadium_day.parquet         : 구장 시군구 × 일 처치변수
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
KBO = ROOT / "data" / "raw" / "kbo"

SIDO = {"11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주", "30": "대전",
        "31": "울산", "36": "세종", "41": "경기", "43": "충북", "44": "충남", "46": "전남",
        "47": "경북", "48": "경남", "50": "제주", "51": "강원", "52": "전북"}
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}


def harmonize_codes(v):
    """2026-07-01 광주·전남 통합(코드 12xxx)을 기존 29xxx/46xxx 코드로 되돌린다."""
    old = v[v.signguCode.str[:2].isin(["29", "46"])][["signguCode", "signguNm"]].drop_duplicates()
    old["prefix"] = old.signguCode.str[:2]
    new = v[v.signguCode.str[:2] == "12"][["signguCode", "signguNm"]].drop_duplicates()
    remap = {}
    for code, nm in new.itertuples(index=False):
        pref = "29" if nm in GWANGJU_GU else "46"
        cand = old[(old.prefix == pref) & (old.signguNm == nm)]
        assert len(cand) == 1, (code, nm, cand)
        remap[code] = cand.signguCode.iloc[0]
    v = v.copy()
    v["signguCode"] = v.signguCode.replace(remap)
    return v, remap


def lowest_units(v, n_days):
    """시 전체 + 일반구가 함께 제공되는 경우 하나만 남긴다(완전한 쪽 우선: 일반구)."""
    names = v[["signguCode", "signguNm"]].drop_duplicates()
    cover = v.groupby("signguCode").date.nunique()
    drop = set()
    subs = names[names.signguNm.str.contains(" ")]
    for city, grp in subs.groupby(subs.signguNm.str.split(" ").str[0]):
        sido = grp.signguCode.iloc[0][:2]
        parent = names[(names.signguNm == city) & (names.signguCode.str[:2] == sido)]
        complete = all(cover[c] == n_days for c in grp.signguCode)
        if complete:
            drop |= set(parent.signguCode)
        else:
            drop |= set(grp.signguCode)
    return drop


def main():
    v = pd.read_parquet(PROC / "visitors_sigungu_daily.parquet")
    v, remap = harmonize_codes(v)
    v = (v.groupby(["signguCode", "date"], as_index=False)
         .agg(signguNm=("signguNm", "first"), local=("local", "sum"),
              outsider=("outsider", "sum"), foreigner=("foreigner", "sum")))
    n_days = v.date.nunique()
    drop = lowest_units(v, n_days)
    v = v[~v.signguCode.isin(drop)]
    cover = v.groupby("signguCode").date.nunique()
    incomplete = cover[cover < n_days].index
    print("dropped parent/sub duplicates:", len(drop), "incomplete units:",
          sorted(v[v.signguCode.isin(incomplete)].signguNm.unique()))
    v = v[~v.signguCode.isin(incomplete)].copy()
    v["sido"] = v.signguCode.str[:2].map(SIDO)
    assert v.sido.notna().all()
    assert (v.outsider > 0).all()

    # --- KBO 경기 ---
    st = pd.read_csv(PROC / "stadium_region.csv", dtype={"signguCode": str})
    g = pd.read_csv(KBO / "games.csv", parse_dates=["date"])
    s = pd.read_csv(KBO / "schedule.csv", parse_dates=["date"])
    g = g.merge(st[["stadium", "signguCode", "is_secondary"]], on="stadium", how="left")
    assert g.signguCode.notna().all(), g[g.signguCode.isna()].stadium.unique()
    g.to_csv(PROC / "kbo_games_clean.csv", index=False, encoding="utf-8-sig")

    s = s.merge(st[["stadium", "signguCode"]], on="stadium", how="left")
    canc = s[s.note != "-"]

    hol = pd.read_csv(KBO / "holidays.csv", parse_dates=["date"])

    # 구장 시군구 × 일 처치변수
    sd = (g.groupby(["signguCode", "date"])
          .agg(n_games=("crowd", "size"), crowd=("crowd", "sum"),
               secondary=("is_secondary", "max"), stadium=("stadium", "first"))
          .reset_index())
    cd = canc.groupby(["signguCode", "date"]).size().rename("n_canceled").reset_index()
    sd = sd.merge(cd, on=["signguCode", "date"], how="outer")
    sd["n_games"] = sd.n_games.fillna(0).astype(int)
    sd["crowd"] = sd.crowd.fillna(0)
    sd["n_canceled"] = sd.n_canceled.fillna(0).astype(int)
    sd.to_parquet(PROC / "stadium_day.parquet", index=False)

    # 정규시즌 종료일 (포스트시즌 기간 제외용)
    season_end = g.groupby("season").date.max()
    season_start = g.groupby("season").date.min()

    p = v.merge(sd[["signguCode", "date", "n_games", "crowd", "n_canceled"]],
                on=["signguCode", "date"], how="left")
    p[["n_games", "crowd", "n_canceled"]] = p[["n_games", "crowd", "n_canceled"]].fillna(0)
    p["game"] = (p.n_games > 0).astype(int)
    p["canceled_only"] = ((p.n_canceled > 0) & (p.n_games == 0)).astype(int)
    p["holiday"] = p.date.isin(hol.date).astype(int)
    p["dow"] = p.date.dt.dayofweek
    p["weekend"] = ((p.dow >= 5) | (p.holiday == 1)).astype(int)
    p["ym"] = p.date.dt.to_period("M").astype(str)
    p["year"] = p.date.dt.year
    # 포스트시즌 창(정규시즌 종료 다음날~11/30)에는 포스트시즌 경기일 정보가 없으므로 표본에서 제외 표시
    p["postseason_window"] = 0
    for yr, end in season_end.items():
        m = (p.date > end) & (p.date <= pd.Timestamp(f"{yr}-11-30"))
        p.loc[m, "postseason_window"] = 1
    p["in_season"] = 0
    for yr in season_start.index:
        m = (p.date >= season_start[yr]) & (p.date <= season_end[yr])
        p.loc[m, "in_season"] = 1
    p["stadium_unit"] = p.signguCode.isin(st.signguCode).astype(int)
    p.to_parquet(PROC / "panel_sigungu_daily.parquet", index=False)
    print("panel:", p.shape, "units", p.signguCode.nunique(), p.date.min().date(), p.date.max().date())
    print("remapped 2026-07 codes:", len(remap))
    print(p[p.stadium_unit == 1].groupby("signguNm").agg(games=("game", "sum"),
                                                         canceled=("canceled_only", "sum")))


if __name__ == "__main__":
    main()
