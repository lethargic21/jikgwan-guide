"""확장 분석: 같은 파이프라인을 K리그1(2024~2025) 홈경기에 적용 — '다른 종목으로의 확산 가능성' 점검.

데이터
- 방문자: data/processed/visitors_sigungu_daily.parquet (이미 받은 데이터랩 API 캐시, 추가 호출 0회)
- 경기: 한국어 위키백과 '2024·2025년 K리그1의 경기 결과'(정규 38라운드) + 시즌 문서의 승강 플레이오프 중 K리그1 구장 홈경기
  (14_fetch_kleague.py가 받은 wikitext, CC BY-SA 4.0, 판 번호는 *.meta.json)
- 경기장 → 시군구: 각 경기장 위키백과 문서의 '위치' (data/processed/kleague_stadium_region.csv)

설계 (KBO 메인 분석 03_gameday_effect.py와 동일)
- 종속변수: d = log(외지인) − 같은 광역 내 '경기장 없는' 도시형 시군구(군 제외, KBO·K리그1 경기장 시군구 제외) 평균
- 통제: 지역×(요일×공휴일), 지역×연월 고정효과. KBO 구장과 같은 시군구(수원 장안구·울산 남구·포항 남구)는 KBO 경기일·취소일 더미 추가
- 표본: 2024-01-01~2025-12-31. 해당 연도에 K리그1 소속이 아니던 구단의 경기장(2024 안양, 2025 인천)은 그 해를 뺀다
  (K리그2 홈경기 일정이 자료에 없어서). 수원 장안구는 KBO 포스트시즌 창(정규시즌 종료 다음날~11/30)을 뺀다
- 표준오차: 경기장별 Newey-West HAC(14일), 통합 Driscoll-Kraay(시간 HAC, 지역 간 상관 허용)
- 관중 수는 위키백과 값(시즌 총관중과 대조)을 쓰되, 효과 추정은 홈경기 여부(0/1)로 한다

출력
- data/processed/kleague_matches.csv, kleague_stadium_region.csv
- outputs/tables/kleague_effect_pooled.csv, kleague_effect_by_stadium.csv, kleague_validation.csv
- outputs/figures/fig6_kleague_event_study.png
"""
import importlib.util
import json
import re
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "kleague"
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
HAC_LAGS = 14
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")

_spec = importlib.util.spec_from_file_location("build_panel", ROOT / "analysis" / "02_build_panel.py")
bp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bp)

# 경기장(위키백과 링크 이름) → 표준 이름
VENUE_ALIAS = {"포항 스틸야드": "포항스틸야드", "대구iM뱅크파크": "대구iM뱅크파크", "DGB대구은행파크": "대구iM뱅크파크",
               "인천축구전용구장": "인천축구전용경기장"}
# 표준 이름 → (위키백과 문서 요청 이름, 시군구 코드, 광역, 시군구, 비고)
STADIUMS = {
    "서울월드컵경기장": ("서울월드컵경기장", "11440", "서울", "마포구", ""),
    "인천축구전용경기장": ("인천축구전용구장", "28110", "인천", "중구",
                    "문서의 현재 주소는 제물포구(2026-07 인천 행정체제 개편). 분석 기간(2024~2025)에는 중구"),
    "수원종합운동장": ("수원종합운동장", "41111", "경기", "수원시 장안구", "KBO 수원KT위즈파크와 같은 시군구 → KBO 경기일 통제"),
    "안양종합운동장": ("안양종합운동장", "41173", "경기", "안양시 동안구", "FC안양은 2025년 K리그1 승격 → 2025년만 분석"),
    "강릉종합운동장": ("강릉종합운동장", "51150", "강원", "강릉시", "강원FC 홈(춘천과 분산)"),
    "춘천송암스포츠타운": ("춘천송암스포츠타운", "51110", "강원", "춘천시", "강원FC 홈(강릉과 분산)"),
    "대전월드컵경기장": ("대전월드컵경기장", "30200", "대전", "유성구", ""),
    "광주축구전용구장": ("광주축구전용구장", "29140", "광주", "서구", "문서의 현재 광역명은 전남광주통합특별시(2026-07)"),
    "광주월드컵경기장": ("광주월드컵경기장", "29140", "광주", "서구", "광주축구전용구장과 같은 부지(풍암동)"),
    "대구iM뱅크파크": ("DGB대구은행파크", "27230", "대구", "북구", "2025년 DGB대구은행파크에서 이름 변경"),
    "울산문수축구경기장": ("울산문수축구경기장", "31140", "울산", "남구", "KBO 문수야구장(제2구장)과 같은 시군구 → KBO 경기일 통제"),
    "울산종합운동장": ("울산종합운동장", "31110", "울산", "중구", "2024년 1경기"),
    "포항스틸야드": ("포항 스틸야드", "47111", "경북", "포항시 남구", "KBO 포항야구장(제2구장)과 같은 시군구 → KBO 경기일 통제"),
    "김천종합운동장": ("김천종합운동장", "47150", "경북", "김천시", ""),
    "전주월드컵경기장": ("전주월드컵경기장", "52113", "전북", "전주시 덕진구", ""),
    "제주월드컵경기장": ("제주월드컵경기장", "50130", "제주", "서귀포시", "광역 내 대조군은 제주시 1곳"),
}
K1_YEARS = {"41173": [2025], "28110": [2024]}
# 관중 수 외부 대조: 한국프로축구연맹 발표(기사 인용). 경기별 위키 값 합계와 비교한다
OFFICIAL_CROWD = [dict(season=2025, through="2025-10-18", label="정규 33라운드 종료 시점 K리그1 누적 유료관중",
                       official=2047564, source="https://sports.news.nate.com/view/20251018n11850 (스포츠조선 2025-10-18, 한국프로축구연맹 발표)")]  # 그 해에만 K리그1 홈경기가 있는 경기장(나머지는 2024·2025 모두)


# ---------------------------------------------------------------- 1) 경기 파싱
def link_target(s):
    m = re.search(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", s)
    return (m.group(1) if m else s).strip()


def parse_matches(txt, season, source, playoff=False):
    rows = []
    heads = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^={2,3}\s*(.+?)\s*={2,3}\s*$", txt, flags=re.M)]
    for m in re.finditer(r"\{\{축구 경기 정보2(.*?)\n\}\}", txt, flags=re.S):
        f = {}
        for line in m.group(1).splitlines():
            mm = re.match(r"^\|\s*([^=|]+?)\s*=\s*(.*)$", line)
            if mm:
                f[mm.group(1).strip()] = mm.group(2).strip()
        d = re.search(r"시작 날짜\|(\d{4})\|(\d{1,2})\|(\d{1,2})", f.get("날짜", ""))
        t = re.search(r"UTZ\|(\d{1,2}:\d{2})", f.get("시간", ""))
        crowd = re.sub(r"[^\d]", "", re.sub(r"<ref.*", "", f.get("관중수", "")))
        head = [h for pos, h in heads if pos < m.start()]
        venue = link_target(f.get("경기장", ""))
        rows.append(dict(season=season, round=head[-1] if head else "", date=pd.Timestamp(int(d[1]), int(d[2]), int(d[3])),
                         time=t[1] if t else "", venue_raw=venue, venue=VENUE_ALIAS.get(venue, venue),
                         home=link_target(f.get("팀1", "")), away=link_target(f.get("팀2", "")),
                         crowd=float(crowd) if crowd else np.nan, promotion_po=playoff, source=source))
    return rows


def load_matches():
    rows, val = [], []
    for season in (2024, 2025):
        txt = (RAW / f"wiki_{season}년_K리그1의_경기_결과.wikitext").read_text(encoding="utf-8")
        meta = json.loads((RAW / f"wiki_{season}년_K리그1의_경기_결과.meta.json").read_text(encoding="utf-8"))
        league = parse_matches(txt, season, meta["permalink"])
        stxt = (RAW / f"wiki_{season}년_K리그1.wikitext").read_text(encoding="utf-8")
        smeta = json.loads((RAW / f"wiki_{season}년_K리그1.meta.json").read_text(encoding="utf-8"))
        po = [r for r in parse_matches(stxt, season, smeta["permalink"], playoff=True) if r["venue"] in STADIUMS]
        total = int(re.sub(r"[^\d]", "", re.search(r"총 관중\s*=\s*([\d,]+)", stxt).group(1)))
        lg = pd.DataFrame(league)
        team = lg.home.str.replace(r"\s|FC", "", regex=True)  # 표기 차이(수원FC/수원 FC, 울산 HD/울산 HD FC 등) 통일
        val.append(dict(season=season, matches=len(lg), teams=team.nunique(),
                        home_games_per_team=f"{team.value_counts().min()}~{team.value_counts().max()}",
                        crowd_missing=int(lg.crowd.isna().sum()), crowd_sum_matches=int(lg.crowd.sum()),
                        wiki_infobox_total=total, diff_vs_infobox_pct=round(100 * (lg.crowd.sum() / total - 1), 2),
                        promotion_po_home_games_at_k1_venues=len(po), source=meta["permalink"], season_source=smeta["permalink"]))
        rows += league + po
    m = pd.DataFrame(rows)
    unknown = set(m.venue) - set(STADIUMS)
    assert not unknown, unknown
    val = pd.DataFrame(val)
    for o in OFFICIAL_CROWD:
        ours = int(m[(m.season == o["season"]) & ~m.promotion_po & (m.date <= o["through"])].crowd.sum())
        i = val.index[val.season == o["season"]][0]
        val.loc[i, "official_check"] = f'{o["label"]}({o["through"]}): 공식 {o["official"]:,} vs 경기별 합계 {ours:,} ({100 * (ours / o["official"] - 1):+.2f}%)'
        val.loc[i, "official_source"] = o["source"]
    return m, val


def stadium_table():
    meta = json.loads((RAW / "stadium_articles" / "_meta.json").read_text(encoding="utf-8"))
    rows = []
    for venue, (req, code, sido, sgg, note) in STADIUMS.items():
        txt = (RAW / "stadium_articles" / f"{req}.wikitext").read_text(encoding="utf-8")
        loc = re.search(r"^\|\s*위치\s*=\s*(.+)$", txt, flags=re.M).group(1)
        loc = re.sub(r"\{\{[^}]*\}\}", "", loc)
        loc = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", loc).strip()
        rows.append(dict(venue=venue, wiki_title=meta[req]["title"], address_in_wiki=loc, sido=sido, sigungu=sgg,
                         signguCode=code, note=note, source=meta[req]["permalink"]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 2) 패널
def build_panel(matches, st):
    v = pd.read_parquet(PROC / "visitors_sigungu_daily.parquet")
    v, _ = bp.harmonize_codes(v)
    v = v[(v.date >= START) & (v.date <= END)]
    v = (v.groupby(["signguCode", "date"], as_index=False)
         .agg(signguNm=("signguNm", "first"), outsider=("outsider", "sum")))
    n_days = v.date.nunique()
    v = v[~v.signguCode.isin(bp.lowest_units(v, n_days))]
    cover = v.groupby("signguCode").date.nunique()
    v = v[v.signguCode.isin(cover[cover == n_days].index)].copy()
    v["sido"] = v.signguCode.str[:2].map(bp.SIDO)
    assert v.sido.notna().all() and (v.outsider > 0).all()

    m = matches.merge(st[["venue", "signguCode"]], on="venue")
    kd = m.groupby(["signguCode", "date"]).agg(kl_games=("home", "size"), kl_crowd=("crowd", "sum"),
                                               kl_crowd_n=("crowd", "count")).reset_index()
    sd = pd.read_parquet(PROC / "stadium_day.parquet")  # KBO 구장 시군구 × 일 (정규·제2구장)
    kbo_units = set(pd.read_csv(PROC / "stadium_region.csv", dtype={"signguCode": str}).signguCode)
    p = (v.merge(kd, on=["signguCode", "date"], how="left")
         .merge(sd[["signguCode", "date", "n_games", "n_canceled"]], on=["signguCode", "date"], how="left"))
    p[["kl_games", "kl_crowd", "kl_crowd_n", "n_games", "n_canceled"]] = \
        p[["kl_games", "kl_crowd", "kl_crowd_n", "n_games", "n_canceled"]].fillna(0)
    p["kl_game"] = (p.kl_games > 0).astype(int)
    p["kbo_game"] = (p.n_games > 0).astype(int)
    p["kbo_canceled"] = ((p.n_canceled > 0) & (p.n_games == 0)).astype(int)
    hol = pd.read_csv(ROOT / "data" / "raw" / "kbo" / "holidays.csv", parse_dates=["date"])
    p["holiday"] = p.date.isin(hol.date).astype(int)
    p["dow"] = p.date.dt.dayofweek
    p["weekend"] = ((p.dow >= 5) | (p.holiday == 1)).astype(int)
    p["ym"] = p.date.dt.to_period("M").astype(str)
    p["year"] = p.date.dt.year
    p["lo"] = np.log(p.outsider)
    # KBO 포스트시즌 창(경기일 정보 없음) — KBO 정규구장 시군구에만 적용
    g = pd.read_csv(PROC / "kbo_games_clean.csv", parse_dates=["date"])
    p["kbo_post_window"] = 0
    main_kbo = set(g[g.is_secondary == 0].signguCode.astype(str))
    for yr, end in g.groupby("season").date.max().items():
        msk = p.signguCode.isin(main_kbo) & (p.date > end) & (p.date <= pd.Timestamp(f"{yr}-11-30"))
        p.loc[msk, "kbo_post_window"] = 1
    p["kl_unit"] = p.signguCode.isin(st.signguCode).astype(int)
    p["kbo_unit"] = p.signguCode.isin(kbo_units).astype(int)
    return p


def diff_series(p, code):
    unit = p[p.signguCode == code].set_index("date").sort_index()
    ctrl = p[(p.kl_unit == 0) & (p.kbo_unit == 0) & (p.sido == unit.sido.iloc[0]) & ~p.signguNm.str.endswith("군")]
    cm = ctrl.groupby("date").lo.mean()
    unit = unit.assign(d=unit.lo - cm, n_ctrl=ctrl.signguCode.nunique(), ctrl_names="·".join(sorted(ctrl.signguNm.unique())))
    # 전후 시차는 날짜가 이어진 전체 계열에서 만든 뒤 표본을 자른다
    unit = add_leads_lags(unit)
    yrs = K1_YEARS.get(code, [2024, 2025])
    return unit[unit.year.isin(yrs) & (unit.kbo_post_window == 0)]


def pct(b):
    return 100 * (np.exp(b) - 1)


def row(res, var, **extra):
    b, se = res.params[var], res.bse[var]
    return dict(var=var, coef=b, se=se, pval=res.pvalues[var], pct=pct(b), pct_lo=pct(b - 1.96 * se),
                pct_hi=pct(b + 1.96 * se), nobs=int(res.nobs), **extra)


def add_leads_lags(u):
    u = u.sort_index().copy()
    for k in range(1, 4):
        u[f"lead{k}"] = u.kl_game.shift(-k).fillna(0)
        u[f"lag{k}"] = u.kl_game.shift(k).fillna(0)
    return u


# ---------------------------------------------------------------- 3) 추정
def fit_unit(u, regs):
    regs = [r for r in regs if u[r].abs().sum() > 0]
    X = pd.concat([u[regs].astype(float),
                   pd.get_dummies(u.dow.astype(str) + "_" + u.holiday.astype(str), prefix="dh", drop_first=True),
                   pd.get_dummies(u.ym, prefix="ym", drop_first=True)], axis=1).astype(float)
    return sm.OLS(u.d.values, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})


def main():
    matches, val = load_matches()
    st = stadium_table()
    matches.to_csv(PROC / "kleague_matches.csv", index=False, encoding="utf-8-sig")
    st.to_csv(PROC / "kleague_stadium_region.csv", index=False, encoding="utf-8-sig")
    p = build_panel(matches, st)

    units = st.groupby("signguCode").agg(sido=("sido", "first"), sigungu=("sigungu", "first"),
                                         venues=("venue", "/".join)).reset_index()
    by, frames, info = [], [], []
    for code, sido, sgg, venues in units.itertuples(index=False):
        u = diff_series(p, code)
        n_game = int(u.kl_game.sum())
        gd = u[u.kl_game == 1]
        base = dict(sigungu=f"{sido} {sgg}", signguCode=code, venues=venues, years="·".join(map(str, K1_YEARS.get(code, [2024, 2025]))),
                    n_game_days=n_game, mean_crowd=gd.kl_crowd.sum() / max(gd.kl_crowd_n.sum(), 1),
                    n_ctrl_units=int(u.n_ctrl.iloc[0]), ctrl_units=u.ctrl_names.iloc[0],
                    kbo_control=int(u.kbo_game.sum() > 0))
        info.append(base)
        if n_game < 5:
            continue
        regs = ["kl_game", "kbo_game", "kbo_canceled"]
        res = fit_unit(u, regs)
        r = row(res, "kl_game", **base)
        b, se = res.params["kl_game"], res.bse["kl_game"]
        for tag, bb in [("point", b), ("lo", b - 1.96 * se), ("hi", b + 1.96 * se)]:
            r[f"extra_outsiders_per_game_{tag}"] = (gd.outsider * (1 - np.exp(-bb))).sum() / n_game
        r["share_of_crowd_point"] = r["extra_outsiders_per_game_point"] / r["mean_crowd"]
        by.append(r)
        frames.append(u.assign(unit=code).reset_index())

    byd = pd.DataFrame(by).sort_values("pct", ascending=False)
    byd.to_csv(TAB / "kleague_effect_by_stadium.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(info).to_csv(TAB / "kleague_units.csv", index=False, encoding="utf-8-sig")

    # 통합(Driscoll-Kraay)
    s = pd.concat(frames, ignore_index=True)
    s["post_only"] = ((s.kl_game == 0) & (s.lag1 == 1)).astype(int)
    s["pre_only"] = ((s.kl_game == 0) & (s.lead1 == 1)).astype(int)
    s["small_city"] = s.signguCode.isin(["47150", "51110", "51150", "50130"]).astype(int)  # 김천·춘천·강릉·서귀포(시 단위)
    fe1 = pd.get_dummies(s.unit + "_" + s.dow.astype(str) + "_" + s.holiday.astype(str))
    first_ym = s.groupby("unit").ym.transform("min")
    fe2 = pd.get_dummies((s.unit + "_" + s.ym).where(s.ym != first_ym))
    s = s.assign(t=pd.factorize(s.date)[0])

    order = np.argsort(s.t.values, kind="stable")

    def run(regs):
        X = pd.concat([s[regs], fe1, fe2], axis=1).astype(float)
        X = X.loc[:, X.abs().sum() > 0]
        assert np.linalg.matrix_rank(X.values) == X.shape[1], "rank deficient"
        X = X.iloc[order]
        return sm.OLS(pd.Series(s.d.values[order], index=X.index), X).fit(
            cov_type="hac-groupsum", cov_kwds={"time": s.t.values[order], "maxlags": HAC_LAGS})

    def rows_of(res, names, spec):
        return [row(res, v, spec=spec) for v in names]

    ctrl = ["kbo_game", "kbo_canceled"]
    out = []
    out += rows_of(run(["kl_game"] + ctrl), ["kl_game"], "pooled")
    s["kl_wkday"] = s.kl_game * (1 - s.weekend)
    s["kl_wkend"] = s.kl_game * s.weekend
    out += rows_of(run(["kl_wkday", "kl_wkend"] + ctrl), ["kl_wkday", "kl_wkend"], "pooled_wk")
    s["kl_small"] = s.kl_game * s.small_city
    s["kl_metro"] = s.kl_game * (1 - s.small_city)
    out += rows_of(run(["kl_small", "kl_metro"] + ctrl), ["kl_small", "kl_metro"], "pooled_city")
    ev = ["lead3", "lead2", "lead1", "kl_game", "lag1", "lag2", "lag3"]
    out += rows_of(run(ev + ctrl), ev, "event_study")
    out += rows_of(run(["kl_game", "post_only", "pre_only"] + ctrl), ["kl_game", "post_only", "pre_only"], "stay")
    # 강건성: KBO 구장과 같은 시군구(수원 장안구·울산 남구·포항 남구)를 뺀 통합 추정
    s["kl_game_nokbo"] = s.kl_game * (1 - s.signguCode.isin(["41111", "31140", "47111"]).astype(int))
    s["kl_game_kbo"] = s.kl_game - s.kl_game_nokbo
    out += rows_of(run(["kl_game_nokbo", "kl_game_kbo"] + ctrl), ["kl_game_nokbo", "kl_game_kbo"], "pooled_kbo_overlap")
    pooled = pd.DataFrame(out)
    gd = s[s.kl_game == 1]
    b = pooled.query("spec=='pooled'").coef.iloc[0]
    se = pooled.query("spec=='pooled'").se.iloc[0]
    for tag, bb in [("point", b), ("lo", b - 1.96 * se), ("hi", b + 1.96 * se)]:
        pooled.loc[pooled.spec == "pooled", f"extra_outsiders_per_game_{tag}"] = (gd.outsider * (1 - np.exp(-bb))).sum() / len(gd)
    pooled.loc[pooled.spec == "pooled", "n_game_days"] = len(gd)
    pooled.loc[pooled.spec == "pooled", "n_units"] = s.unit.nunique()
    pooled.loc[pooled.spec == "pooled", "mean_crowd"] = gd.kl_crowd.sum() / gd.kl_crowd_n.sum()
    pooled.to_csv(TAB / "kleague_effect_pooled.csv", index=False, encoding="utf-8-sig")
    val.to_csv(TAB / "kleague_validation.csv", index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    print(val.to_string())
    print(pooled[["spec", "var", "pct", "pct_lo", "pct_hi", "pval", "nobs"]].round(3).to_string())
    print(pooled.query("spec=='pooled'")[["n_units", "n_game_days", "mean_crowd", "extra_outsiders_per_game_point",
                                          "extra_outsiders_per_game_lo", "extra_outsiders_per_game_hi"]].round(0).to_string())
    print(byd[["sigungu", "venues", "years", "n_game_days", "mean_crowd", "pct", "pct_lo", "pct_hi", "pval",
               "extra_outsiders_per_game_point", "n_ctrl_units", "kbo_control"]].round(3).to_string())
    fig_event(pooled)


# ---------------------------------------------------------------- 4) 그림
INK, INK2, GRID, BLUE = "#0b0b0b", "#52514e", "#d9d8d4", "#2a78d6"
plt.rcParams.update({
    "font.family": "Noto Sans KR", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlecolor": INK,
})


def fig_event(pooled):
    d = pooled[pooled.spec == "event_study"].set_index("var")
    order = ["lead3", "lead2", "lead1", "kl_game", "lag1", "lag2", "lag3"]
    labels = ["D-3", "D-2", "D-1", "경기일", "D+1", "D+2", "D+3"]
    d = d.loc[order]
    x = range(len(order))
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.axhline(0, color=INK2, lw=0.8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.vlines(x, d.pct_lo, d.pct_hi, color=INK, lw=1.4)
    sig = d.pval < 0.05
    ax.plot([i for i, s_ in zip(x, sig) if s_], d.pct[sig], "o", ms=7, color=BLUE, mec="white", mew=1.5, zorder=3)
    ax.plot([i for i, s_ in zip(x, sig) if not s_], d.pct[~sig], "o", ms=7, color="white", mec=BLUE, mew=1.5, zorder=3)
    g = d.loc["kl_game"]
    ax.annotate(f"{g.pct:+.1f}%\n(95% CI {g.pct_lo:.1f}~{g.pct_hi:.1f})", (3, g.pct), xytext=(14, -6),
                textcoords="offset points", color=INK, fontsize=9, va="center")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("외지인 방문자 변화 (%)")
    near = d.loc[["lead1", "lag1"]]
    same_day_only = (g.pval < 0.05) and (near.pval >= 0.05).all()
    title = ("K리그1도 경기날만 늘고 전날·다음날은 0" if same_day_only
             else "K리그1 홈경기일 전후 외지인 변화")
    ax.set_title(title, loc="left")
    n_units = int(pooled.query("spec=='pooled'").n_units.iloc[0])
    ax.text(0, -0.2, f"K리그1 경기장 소재 {n_units}개 시군구 통합(2024~2025, 정규 38라운드+승강PO 홈경기). 같은 광역 내 경기장 없는 도시형 시군구 대비,\n"
            "지역×요일·공휴일, 지역×연월 고정효과, KBO 경기일 통제. 채운 점: p<0.05, 세로선=95% CI(Driscoll-Kraay).\n"
            "자료: 한국관광 데이터랩(지역별 방문자수), 한국어 위키백과 'K리그1의 경기 결과'(CC BY-SA)",
            transform=ax.transAxes, fontsize=7, color=INK2, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "fig6_kleague_event_study.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
