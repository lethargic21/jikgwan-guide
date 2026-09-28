"""A. 경기일 효과 (메인 분석).

설계
- 단위: 구장 소재 시군구 × 일.
- 종속변수: d_t = log(외지인_it) − 같은 광역 내 비구장 도시형 시군구(자치구·시·일반구, 군 제외)의 log(외지인) 평균.
  → 패널 모형의 '광역×날짜 고정효과'와 동일하다. 같은 날 같은 광역의 날씨·연휴·전국 충격을 흡수한다.
  → 군(郡) 제외 이유: 구장 시군구는 모두 도시형 단위인데, 섬·농산어촌 군(강화·옹진·기장·달성·울주 등)은
    비 오는 날 방문이 훨씬 크게 줄어 우천일에 '가짜 차이'를 만든다(문학: 전체 대조군이면 취소일 +10.8% > 경기일 +6.3%).
    전체 대조군 결과는 강건성 표(gameday_effect_by_stadium_sido_allctrl.csv)로 남긴다.
- 통제: 지역×(요일×공휴일) 고정효과, 지역×연월 고정효과. 우천 등 취소일 더미를 따로 넣는다.
- 표본: 포스트시즌 창(정규시즌 종료 다음날~11/30)은 경기일 정보가 없어 제외한다.
- 표준오차: 구장별 추정은 처치 지역이 1개라 지역 클러스터가 불가능하다 → Newey-West HAC(14일 시차).
  구장 통합(pooled) 추정은 Driscoll-Kraay(시간 HAC + 지역 간 상관 허용).

출력: outputs/tables/gameday_*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "outputs" / "tables"
TAB.mkdir(parents=True, exist_ok=True)
HAC_LAGS = 14
MAIN_CONTROL = "sido_urban"


def load():
    p = pd.read_parquet(PROC / "panel_sigungu_daily.parquet")
    st = pd.read_csv(PROC / "stadium_region.csv", dtype={"signguCode": str})
    p["lo"] = np.log(p.outsider)
    p["crowd10k"] = p.crowd / 1e4
    return p, st


def diff_series(p, code, control=MAIN_CONTROL):
    """처치 지역의 log 외지인 − 대조군 평균. control: sido_urban(주) / sido(광역 전체) / nation(전국)."""
    unit = p[p.signguCode == code].set_index("date").sort_index()
    ctrl = p[p.stadium_unit == 0]
    if control in ("sido", "sido_urban"):
        ctrl = ctrl[ctrl.sido == unit.sido.iloc[0]]
    if control == "sido_urban":
        ctrl = ctrl[~ctrl.signguNm.str.endswith("군")]
    cm = ctrl.groupby("date").lo.mean()
    unit = unit.assign(d=unit.lo - cm, n_ctrl=ctrl.signguCode.nunique())
    return unit


def fe_design(u, regs):
    regs = [r for r in regs if u[r].abs().sum() > 0]  # 고척(돔)처럼 취소일이 없으면 제외
    X = u[regs].astype(float)
    fe1 = pd.get_dummies(u.dow.astype(str) + "_" + u.holiday.astype(str), prefix="dh", drop_first=True)
    fe2 = pd.get_dummies(u.ym, prefix="ym", drop_first=True)
    X = pd.concat([X, fe1, fe2], axis=1).astype(float)
    return sm.add_constant(X)


def fit_unit(u, regs, y="d"):
    u = u[u.postseason_window == 0]
    X = fe_design(u, regs)
    return sm.OLS(u[y].values, X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS}), u


def pct(b):
    return 100 * (np.exp(b) - 1)


def row(res, var, **extra):
    b, se = res.params[var], res.bse[var]
    lo, hi = b - 1.96 * se, b + 1.96 * se
    return dict(var=var, coef=b, se=se, pval=res.pvalues[var], pct=pct(b), pct_lo=pct(lo), pct_hi=pct(hi),
                nobs=int(res.nobs), **extra)


def main():
    p, st = load()
    units = (st.drop_duplicates("signguCode")[["signguCode", "sido", "sigungu", "is_secondary"]]
             .merge(st.groupby("signguCode").stadium.agg("/".join).rename("stadiums"), on="signguCode"))
    # 대전 중구는 한밭(2023-24)과 신구장(2025-26)을 같은 단위로 추정
    units["label"] = units.stadiums.str.replace("한밭/대전", "대전(한밭·신구장)")

    rows, rows_nat, rows_all, rows_crowd, rows_het, share, pair25, events, stay = [], [], [], [], [], [], [], [], []
    for code, sido, sgg, sec, label in units[["signguCode", "sido", "sigungu", "is_secondary", "label"]].itertuples(index=False):
        u = diff_series(p, code)
        n_ctrl = int(u.n_ctrl.iloc[0])

        res, uu = fit_unit(u, ["game", "canceled_only"])
        base = dict(stadium=label, sido=sido, sigungu=sgg, signguCode=code, secondary=sec,
                    n_game_days=int(uu.game.sum()), n_canceled_days=int(uu.canceled_only.sum()), n_ctrl_units=n_ctrl)
        rows.append(row(res, "game", **base))
        if uu.canceled_only.sum() >= 5:
            rows.append(row(res, "canceled_only", **base))

        # 전국 대조군 (강건성)
        un = diff_series(p, code, "nation")
        resn, _ = fit_unit(un, ["game", "canceled_only"])
        rows_nat.append(row(resn, "game", **base))
        # 광역 전체 대조군(군 포함) (강건성)
        ua = diff_series(p, code, "sido")
        resa, _ = fit_unit(ua, ["game", "canceled_only"])
        rows_all.append(row(resa, "game", **base))
        if uu.canceled_only.sum() >= 5:
            rows_all.append(row(resa, "canceled_only", **base))

        if sec:
            continue
        # 구장별 이벤트 스터디(±3일 분포시차) → D+1 계수 = '경기 다음날 잔존 효과'(체류 지표, 사분면 y축)
        ue = u.copy()
        for k in range(1, 4):
            ue[f"lead{k}"] = ue.game.shift(-k).fillna(0)
            ue[f"lag{k}"] = ue.game.shift(k).fillna(0)
        ev = ["lead3", "lead2", "lead1", "game", "lag1", "lag2", "lag3"]
        re_, _ = fit_unit(ue, ev + ["canceled_only"])
        events += [row(re_, v, k=ev.index(v) - 3, **base) for v in ev]
        # 연전 경계일: 경기 없는 다음날(post_only)·경기 없는 전날(pre_only) → 숙박·체류 여부를 더 직접 본다
        ue["post_only"] = ((ue.game == 0) & (ue.game.shift(1) == 1)).astype(int)
        ue["pre_only"] = ((ue.game == 0) & (ue.game.shift(-1) == 1)).astype(int)
        rs, us = fit_unit(ue, ["game", "post_only", "pre_only", "canceled_only"])
        for v in ["game", "post_only", "pre_only"]:
            stay.append(row(rs, v, n_days=int(us[v].sum()), **base))

        # 관중 수(만 명) 연속 처치
        rc, _ = fit_unit(u, ["crowd10k", "canceled_only"])
        rows_crowd.append(row(rc, "crowd10k", **base))

        # 평일 vs 주말·공휴일
        u2 = u.assign(game_wkday=u.game * (1 - u.weekend), game_wkend=u.game * u.weekend)
        rh, _ = fit_unit(u2, ["game_wkday", "game_wkend", "canceled_only"])
        rows_het.append(row(rh, "game_wkday", **base))
        rows_het.append(row(rh, "game_wkend", **base))
        # 연도별
        yrs = sorted(uu[uu.game == 1].year.unique())
        u3 = u.copy()
        for yr in yrs:
            u3[f"game_{yr}"] = u3.game * (u3.year == yr)
        ry, _ = fit_unit(u3, [f"game_{yr}" for yr in yrs] + ["canceled_only"])
        for yr in yrs:
            rows_het.append(row(ry, f"game_{yr}", **base))

        # D1(관광지출, 2025-04~09)과 짝을 맞추기 위한 같은 기간 경기당 외지인 증가
        if "game_2025" in ry.params:
            b25, se25 = ry.params["game_2025"], ry.bse["game_2025"]
            g25 = uu[(uu.game == 1) & (uu.index >= "2025-04-01") & (uu.index <= "2025-09-30")]
            rec = dict(stadium=label, n_game_days=len(g25), mean_crowd=g25.crowd.mean(),
                       pct=pct(b25), pct_lo=pct(b25 - 1.96 * se25), pct_hi=pct(b25 + 1.96 * se25))
            for tag, bb in [("point", b25), ("lo", b25 - 1.96 * se25), ("hi", b25 + 1.96 * se25)]:
                rec[f"extra_outsiders_per_game_{tag}"] = (g25.outsider * (1 - np.exp(-bb))).sum() / len(g25)
            pair25.append(rec)

        # 경기일 외지인 증가분 ÷ 관중 수 → '관중 중 (시군구 기준) 외지인 비율' 근사
        b = res.params["game"]
        se = res.bse["game"]
        gd = uu[uu.game == 1]
        for tag, bb in [("point", b), ("lo", b - 1.96 * se), ("hi", b + 1.96 * se)]:
            extra = (gd.outsider * (1 - np.exp(-bb))).sum()
            share.append(dict(stadium=label, bound=tag, extra_outsiders_per_game=extra / len(gd),
                              mean_crowd=gd.crowd.mean(), share_of_crowd=extra / gd.crowd.sum(),
                              mean_outsider_gameday=gd.outsider.mean()))

    out = pd.DataFrame(rows)
    out.to_csv(TAB / "gameday_effect_by_stadium.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rows_nat).to_csv(TAB / "gameday_effect_by_stadium_national_ctrl.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rows_all).to_csv(TAB / "gameday_effect_by_stadium_sido_allctrl.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(stay).to_csv(TAB / "gameday_stay_by_stadium.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(events).to_csv(TAB / "gameday_event_by_stadium.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(pair25).to_csv(TAB / "gameday_outsiders_2025AprSep.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rows_crowd).to_csv(TAB / "gameday_effect_per10k_crowd.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rows_het).to_csv(TAB / "gameday_effect_heterogeneity.csv", index=False, encoding="utf-8-sig")
    sh = pd.DataFrame(share).pivot(index="stadium", columns="bound")
    sh.columns = [f"{a}_{b}" for a, b in sh.columns]
    sh.reset_index().to_csv(TAB / "gameday_outsider_share_of_crowd.csv", index=False, encoding="utf-8-sig")

    pooled(p, units)

    pd.set_option("display.width", 200)
    print(out[["stadium", "var", "pct", "pct_lo", "pct_hi", "pval", "n_game_days", "n_canceled_days"]].round(3).to_string())
    print(pd.DataFrame(rows_nat)[["stadium", "pct", "pct_lo", "pct_hi"]].round(2).to_string())
    print(pd.DataFrame(rows_all)[["stadium", "var", "pct", "pct_lo", "pct_hi"]].round(2).to_string())
    print(pd.DataFrame(rows_crowd)[["stadium", "pct", "pct_lo", "pct_hi"]].round(2).to_string())
    print(pd.DataFrame(rows_het)[["stadium", "var", "pct", "pct_lo", "pct_hi"]].round(2).to_string())
    print(sh.round(3).to_string())


def pooled(p, units):
    """정규구장 통합 추정 + 이벤트 스터디(±3일 분포시차)."""
    main_units = units[units.is_secondary == 0]
    frames = []
    for code, label in main_units[["signguCode", "label"]].itertuples(index=False):
        u = diff_series(p, code).reset_index()
        u = u.sort_values("date")
        for k in range(1, 4):
            u[f"lead{k}"] = u.game.shift(-k).fillna(0)   # k일 뒤 경기 (경기 전날 등)
            u[f"lag{k}"] = u.game.shift(k).fillna(0)     # k일 전 경기 (경기 다음날 등)
        u["post_only"] = ((u.game == 0) & (u.lag1 == 1)).astype(int)
        u["pre_only"] = ((u.game == 0) & (u.lead1 == 1)).astype(int)
        u["unit"] = label
        frames.append(u)
    s = pd.concat(frames, ignore_index=True)
    s = s[s.postseason_window == 0].reset_index(drop=True)
    # 지역×(요일×공휴일)은 전체 수준, 지역×연월은 지역마다 첫 달을 기준으로 빼서 공선성을 없앤다(상수항 없음)
    fe1 = pd.get_dummies(s.unit + "_" + s.dow.astype(str) + "_" + s.holiday.astype(str))
    first_ym = s.groupby("unit").ym.transform("min")
    fe2 = pd.get_dummies((s.unit + "_" + s.ym).where(s.ym != first_ym))
    t_index = pd.factorize(s.date)[0]
    s = s.assign(t=t_index).sort_values("t")
    fe1, fe2 = fe1.loc[s.index], fe2.loc[s.index]

    def run(regs):
        X = pd.concat([s[regs], fe1, fe2], axis=1).astype(float)
        assert np.linalg.matrix_rank(X.values) == X.shape[1], "rank deficient"
        return sm.OLS(s.d.values, X).fit(cov_type="hac-groupsum",
                                         cov_kwds={"time": s.t.values, "maxlags": HAC_LAGS})

    rows = []
    r0 = run(["game", "canceled_only"])
    rows += [row(r0, "game", spec="pooled"), row(r0, "canceled_only", spec="pooled")]
    s["game_wkday"] = s.game * (1 - s.weekend)
    s["game_wkend"] = s.game * s.weekend
    r1 = run(["game_wkday", "game_wkend", "canceled_only"])
    rows += [row(r1, "game_wkday", spec="pooled_wk"), row(r1, "game_wkend", spec="pooled_wk")]
    ev = ["lead3", "lead2", "lead1", "game", "lag1", "lag2", "lag3"]
    r2 = run(ev + ["canceled_only"])
    rows += [row(r2, v, spec="event_study") for v in ev]
    r3 = run(["game", "post_only", "pre_only", "canceled_only"])
    rows += [row(r3, v, spec="stay") for v in ["game", "post_only", "pre_only"]]
    pd.DataFrame(rows).to_csv(TAB / "gameday_effect_pooled.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows)[["spec", "var", "pct", "pct_lo", "pct_hi", "pval", "nobs"]].round(3).to_string())


if __name__ == "__main__":
    main()
