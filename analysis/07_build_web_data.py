"""가이드 웹 데이터 생성 → web/data/guide-data.js (window.GUIDE_DATA).

- 분석 A 수치: outputs/tables/gameday_effect_by_stadium.csv, gameday_outsider_share_of_crowd.csv, gameday_effect_pooled.csv
- 장소: data/processed/tour_places.csv (TourAPI). 이름·분류·거리·주소만 쓴다(영업시간·가격 없음, §3-6).
- 데이터랩 중심-연관 관광지(D2): data/processed/datalab_pre_course.csv, outputs/tables/d2_stadium_rank.csv (analysis/10_datalab_d2.py)
"""
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
OUT = ROOT / "web" / "data"

META = {  # KBO 구장명 → 표시 정보 (텍스트만, 로고·사진 없음 §3-3)
    "잠실": dict(id="jamsil", name="잠실야구장", teams=["LG", "두산"], effect_key="잠실"),
    "고척": dict(id="gocheok", name="고척스카이돔", teams=["키움"], effect_key="고척"),
    "문학": dict(id="munhak", name="인천SSG랜더스필드", teams=["SSG"], effect_key="문학"),
    "수원": dict(id="suwon", name="수원KT위즈파크", teams=["KT"], effect_key="수원"),
    "대전": dict(id="daejeon", name="대전 한화생명볼파크", teams=["한화"], effect_key="대전(한밭·신구장)"),
    "대구": dict(id="daegu", name="대구삼성라이온즈파크", teams=["삼성"], effect_key="대구"),
    "광주": dict(id="gwangju", name="광주-기아챔피언스필드", teams=["KIA"], effect_key="광주"),
    "사직": dict(id="sajik", name="사직야구장", teams=["롯데"], effect_key="사직"),
    "창원": dict(id="changwon", name="창원NC파크", teams=["NC"], effect_key="창원"),
}
N_PRE, N_POST, N_STAY = 8, 8, 6
EVENT_TITLE = re.compile(r"^\s*(19|20)\d{2}\s")  # '2025 ○○페어' 같은 기간 한정 행사는 제외


def place(r):
    return dict(title=r.title, cat=r.cls3_name or r.type, dist=int(r.dist_m), addr=r.addr, type=r.type)


def main():
    eff = pd.read_csv(TAB / "gameday_effect_by_stadium.csv")
    eff = eff[eff["var"] == "game"].set_index("stadium")
    share = pd.read_csv(TAB / "gameday_outsider_share_of_crowd.csv").set_index("stadium")
    pooled = pd.read_csv(TAB / "gameday_effect_pooled.csv")
    pg = pooled[(pooled.spec == "pooled") & (pooled["var"] == "game")].iloc[0]
    sts = pd.read_csv(PROC / "tour_stadiums.csv").set_index("stadium")
    pl = pd.read_csv(PROC / "tour_places.csv").fillna("")
    pl = pl[~pl.title.str.match(EVENT_TITLE)].drop_duplicates(["stadium", "contentid"])
    dl = pd.read_csv(PROC / "datalab_pre_course.csv")
    ds = pd.read_csv(PROC / "datalab_stay.csv")
    rk = pd.read_csv(TAB / "d2_stadium_rank.csv").set_index("stadium")

    stadiums = []
    for key, m in META.items():
        e, s, st = eff.loc[m["effect_key"]], share.loc[m["effect_key"]], sts.loc[key]
        p = pl[pl.stadium == key].sort_values("dist_m")
        pre = p[p.type.isin(["관광지", "문화시설"])].head(N_PRE)
        post = p[p.type == "음식점"].head(N_POST)
        stay = p[p.type == "숙박"].head(N_STAY)
        stadiums.append(dict(
            id=m["id"], key=key, name=m["name"], teams=m["teams"],
            sido=e.sido, sigungu=e.sigungu, addr=st.addr, lat=round(st.mapy, 6), lng=round(st.mapx, 6),
            effect=dict(pct=round(e.pct, 1), lo=round(e.pct_lo, 1), hi=round(e.pct_hi, 1),
                        game_days=int(e.n_game_days),
                        extra_per_game=int(round(s.extra_outsiders_per_game_point, -2)),
                        share_of_crowd=round(100 * s.share_of_crowd_point)),
            datalab_rank=int(rk.loc[key, "rank"]) if pd.notna(rk.loc[key, "rank"]) else None,
            pre_datalab=[dict(title=r.title.replace("/", " "), cat=r.cat, rank=int(r.rank), source=r.source, sigungu=r.sigungu)
                         for r in dl[dl.stadium == key].itertuples()],
            stay_datalab=[dict(title=r.title.replace("/", " "), rank=int(r.rank), source=r.source, sigungu=r.sigungu)
                          for r in ds[ds.stadium == key].itertuples()],
            pre=[place(r) for r in pre.itertuples()],
            post=[place(r) for r in post.itertuples()],
            stay=[place(r) for r in stay.itertuples()],
        ))
    # 정규 9개 구장 전체: 추가 외지인 합계 ÷ 관중 합계 (구장별 경기일 수 가중)
    main_eff = eff[eff.secondary == 0]
    sh = share.join(main_eff.n_game_days, how="inner")
    overall_share = ((sh.extra_outsiders_per_game_point * sh.n_game_days).sum()
                     / (sh.mean_crowd_point * sh.n_game_days).sum())
    data = dict(
        generated=date.today().isoformat(),
        summary=dict(pct=round(pg.pct, 1), lo=round(pg.pct_lo, 1), hi=round(pg.pct_hi, 1),
                     share_of_crowd=round(100 * overall_share),
                     game_days=int(eff[eff.secondary == 0].n_game_days.sum()),
                     period="2023.1~2026.8"),
        stadiums=stadiums,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    js = "// 자동 생성: analysis/07_build_web_data.py — 직접 고치지 말 것\nwindow.GUIDE_DATA = " + \
        json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
    (OUT / "guide-data.js").write_text(js, encoding="utf-8")
    print("stadiums", len(stadiums), "summary", data["summary"])
    for s in stadiums:
        print(s["key"], s["effect"], len(s["pre"]), len(s["post"]), len(s["stay"]))


if __name__ == "__main__":
    main()
