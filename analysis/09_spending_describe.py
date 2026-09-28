"""D1 관광지출 — 서술 통계만 (보조 자료, CLAUDE.md §6-B 2026-09-29 확정).

자료: 데이터랩 빅데이터 › 신용카드 › 지역별 관광지출액, 구장 소재 시군구 9곳, 2025년 1~12월 월별
  (data/raw/datalab/D1/: 관광소비 추이 = 월별·중분류 소비액(천원), 업종별 지출액 = 대·중분류 비율, 지역별 지출액 = 행정동 비율)
- 업종별 구성(특히 숙박 비중), 시즌(4~9월) vs 비시즌(1~3월·10~12월) 비교, 구장 소재 행정동의 비중
- 인과로 해석하지 않는다: 월별 자료라 경기 효과와 계절성(날씨·방학·휴가철)이 섞여 있다. 회귀 추정은 하지 않는다.

출력: outputs/tables/d1_summary.csv, d1_category_share.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D1 = ROOT / "data" / "raw" / "datalab" / "D1"
TAB = ROOT / "outputs" / "tables"
SEASON_MONTHS = range(4, 10)  # 4~9월
STADIUM_DONG = {"잠실": "잠실2동", "고척": "고척1동", "문학": "문학동", "수원": "조원1동", "대전": "부사동",
                "대구": "고산2동", "광주": "임동", "사직": "사직2동", "창원": "양덕2동"}


def load_d1():
    """반환: DataFrame[stadium, sigungu, month(1~12), category(중분류), major(대분류), spend(천원)]"""
    files = sorted(D1.glob("*_관광소비 추이.csv"))
    if not files:
        raise SystemExit("D1 파일이 없음: analysis/00_organize_datalab.py로 zip을 먼저 정리할 것")
    frames = []
    for f in files:
        stadium = f.name.split("_")[0]
        d = pd.read_csv(f)
        major = pd.read_csv(f.with_name(f.name.replace("관광소비 추이", "업종별 지출액")))
        d = d[d["중분류"] != "관광총소비"].merge(major[["대분류", "중분류"]], on="중분류", how="left")
        assert d["대분류"].notna().all(), f.name
        frames.append(pd.DataFrame(dict(stadium=stadium, sigungu=d["기초지자체"], month=d["기준년월"] % 100,
                                        category=d["중분류"], major=d["대분류"], spend=d["소비액(천원)"])))
    return pd.concat(frames, ignore_index=True)


def dong_share(stadium):
    f = next(D1.glob(f"{stadium}_*_지역별 지출액.csv"))
    d = pd.read_csv(f)
    row = d[d["행정동명"] == STADIUM_DONG[stadium]]
    return float(row["비율(%)"].iloc[0]) if len(row) else float("nan"), int(d["비율(%)"].rank(ascending=False)[row.index].iloc[0]) if len(row) else None, len(d)


def main():
    d = load_d1()
    d["season"] = d.month.isin(SEASON_MONTHS)
    rows = []
    for st, g in d.groupby("stadium", sort=False):
        tot = g.spend.sum()
        lodge = g[g.major == "숙박업"].spend.sum()
        s_on, s_off = g[g.season], g[~g.season]
        on_m, off_m = s_on.spend.sum() / 6, s_off.spend.sum() / 6
        share, rank, n_dong = dong_share(st)
        rows.append(dict(
            stadium=st, sigungu=g.sigungu.iloc[0],
            total_2025_억원=tot / 1e5,                       # 천원 → 억원
            lodging_share_pct=100 * lodge / tot,
            lodging_share_season_pct=100 * s_on[s_on.major == "숙박업"].spend.sum() / s_on.spend.sum(),
            lodging_share_off_pct=100 * s_off[s_off.major == "숙박업"].spend.sum() / s_off.spend.sum(),
            monthly_season_억원=on_m / 1e5, monthly_off_억원=off_m / 1e5,
            season_vs_off_pct=100 * (on_m / off_m - 1),
            lodging_season_vs_off_pct=100 * (s_on[s_on.major == "숙박업"].spend.sum()
                                             / s_off[s_off.major == "숙박업"].spend.sum() - 1),
            food_share_pct=100 * g[g.major == "식음료업"].spend.sum() / tot,
            shopping_share_pct=100 * g[g.major == "쇼핑업"].spend.sum() / tot,
            stadium_dong=STADIUM_DONG[st], stadium_dong_share_pct=share, stadium_dong_rank=rank, n_dong=n_dong,
        ))
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "d1_summary.csv", index=False, encoding="utf-8-sig")
    cat = (d.groupby(["stadium", "major"]).spend.sum() / d.groupby("stadium").spend.sum() * 100)
    cat.rename("share_pct").reset_index().to_csv(TAB / "d1_category_share.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    print(out.round(1).to_string())
    print(cat.unstack().round(1).to_string())


if __name__ == "__main__":
    main()
