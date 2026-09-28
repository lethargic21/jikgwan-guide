"""A-보조. 광역 단위 원정팬 효과.

데이터랩 광역 '외지인' = 해당 시·도 비거주자 → 타 광역에서 온 방문(원정팬 포함)에 가깝다.
모형: log(광역 외지인_st) = Σ_s β_s·경기수_st + 날짜 FE + 광역×(요일×공휴일) FE + 광역×연월 FE
- 17개 시·도 패널. 구장이 없는 시·도(세종·강원·충남·전북·전남·제주 등)가 날짜 FE의 기준이 된다.
- 2026-07-01부터 광주·전남이 통합 코드(12)로 바뀌므로 2026-06-30까지만 쓴다.
- 고정효과는 교대 투영(alternating projections)으로 제거, 표준오차는 Driscoll-Kraay.
- 이벤트 스터디: 광역 경기 수의 ±3일 분포시차 → 경기 전날·다음날에 광역 전체(구 밖 숙박 포함) 외지인이 남는지 확인
출력: outputs/tables/sido_gameday_effect.csv, sido_event_study.csv, sido_stay.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
KBO = ROOT / "data" / "raw" / "kbo"
TAB = ROOT / "outputs" / "tables"
SIDO = {"11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주", "30": "대전", "31": "울산",
        "36": "세종", "41": "경기", "43": "충북", "44": "충남", "46": "전남", "47": "경북", "48": "경남",
        "50": "제주", "51": "강원", "52": "전북"}


def demean(df, cols, fes, tol=1e-10, max_iter=500):
    out = df[cols].astype(float).copy()
    for _ in range(max_iter):
        prev = out.copy()
        for fe in fes:
            out -= out.groupby(df[fe]).transform("mean")
        if np.nanmax(np.abs(out.values - prev.values)) < tol:
            break
    return out


def main():
    m = pd.read_parquet(PROC / "visitors_sido_daily.parquet")
    m = m[(m.sidoCode != "12") & (m.date <= "2026-06-30")].copy()
    m["sido"] = m.sidoCode.map(SIDO)
    g = pd.read_csv(PROC / "kbo_games_clean.csv", dtype={"signguCode": str}, parse_dates=["date"])
    g["sidoCode"] = g.signguCode.str[:2]
    gd = g.groupby(["sidoCode", "date"]).agg(n_games=("crowd", "size"), crowd=("crowd", "sum")).reset_index()
    m = m.merge(gd, on=["sidoCode", "date"], how="left").fillna({"n_games": 0, "crowd": 0})
    hol = pd.read_csv(KBO / "holidays.csv", parse_dates=["date"])
    season_end = g.groupby("season").date.max()
    m["post"] = 0
    for yr, end in season_end.items():
        m.loc[(m.date > end) & (m.date <= f"{yr}-11-30"), "post"] = 1
    m = m.sort_values(["sido", "date"])
    for k in range(1, 4):  # 광역별 경기 수의 전후 시차 (표본 제외 전에 계산)
        m[f"lead{k}"] = m.groupby("sido").n_games.shift(-k).fillna(0)
        m[f"lag{k}"] = m.groupby("sido").n_games.shift(k).fillna(0)
    m = m[m.post == 0].copy()
    m["lo"] = np.log(m.outsider)
    m["dh"] = m.sido + "_" + m.date.dt.dayofweek.astype(str) + "_" + m.date.isin(hol.date).astype(str)
    m["sym"] = m.sido + "_" + m.date.dt.to_period("M").astype(str)
    m["dt"] = m.date.astype(str)

    stadium_sido = sorted(m.loc[m.n_games > 0, "sido"].unique())
    regs = []
    for s in stadium_sido:
        m[f"g_{s}"] = m.n_games * (m.sido == s)
        regs.append(f"g_{s}")
    dm = demean(m, ["lo"] + regs, ["dt", "dh", "sym"])
    t = pd.factorize(m.date)[0]
    order = np.argsort(t, kind="stable")
    res = sm.OLS(dm["lo"].values[order], dm[regs].values[order]).fit(
        cov_type="hac-groupsum", cov_kwds={"time": t[order], "maxlags": 14})

    rows = []
    for i, s in enumerate(stadium_sido):
        b, se = res.params[i], res.bse[i]
        gdays = m[(m.sido == s) & (m.n_games > 0)]
        def extra_at(bb):
            return (gdays.outsider * (1 - np.exp(-bb * gdays.n_games))).sum()
        extra = extra_at(b)
        rows.append(dict(share_lo=extra_at(b - 1.96 * se) / gdays.crowd.sum(),
                         share_hi=extra_at(b + 1.96 * se) / gdays.crowd.sum(),sido=s, coef=b, se=se, pval=res.pvalues[i],
                         pct_per_game=100 * (np.exp(b) - 1),
                         pct_lo=100 * (np.exp(b - 1.96 * se) - 1), pct_hi=100 * (np.exp(b + 1.96 * se) - 1),
                         n_game_days=len(gdays), games=int(gdays.n_games.sum()),
                         extra_outsiders_per_game=extra / gdays.n_games.sum(),
                         mean_crowd_per_game=gdays.crowd.sum() / gdays.n_games.sum(),
                         share_other_sido_of_crowd=extra / gdays.crowd.sum()))
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "sido_gameday_effect.csv", index=False, encoding="utf-8-sig")

    # 이벤트 스터디: 광역별 D-3~D+3
    ks = ["lead3", "lead2", "lead1", "n_games", "lag1", "lag2", "lag3"]
    eregs = []
    for s_ in stadium_sido:
        for k in ks:
            m[f"e_{s_}_{k}"] = m[k] * (m.sido == s_)
            eregs.append(f"e_{s_}_{k}")
    dm2 = demean(m, ["lo"] + eregs, ["dt", "dh", "sym"])
    res2 = sm.OLS(dm2["lo"].values[order], dm2[eregs].values[order]).fit(
        cov_type="hac-groupsum", cov_kwds={"time": t[order], "maxlags": 14})
    erows = []
    for i, r in enumerate(eregs):
        _, s_, k = r.split("_", 2)
        b, se = res2.params[i], res2.bse[i]
        erows.append(dict(sido=s_, var=k, k=ks.index(k) - 3, coef=b, se=se, pval=res2.pvalues[i],
                          pct=100 * (np.exp(b) - 1), pct_lo=100 * (np.exp(b - 1.96 * se) - 1),
                          pct_hi=100 * (np.exp(b + 1.96 * se) - 1)))
    # 연전 경계일: 광역에 경기 없는 다음날·전날
    m["post_only"] = ((m.n_games == 0) & (m.lag1 > 0)).astype(int)
    m["pre_only"] = ((m.n_games == 0) & (m.lead1 > 0)).astype(int)
    sregs = []
    for s_ in stadium_sido:
        for k in ["n_games", "post_only", "pre_only"]:
            m[f"s_{s_}_{k}"] = m[k] * (m.sido == s_)
            sregs.append(f"s_{s_}_{k}")
    dm3 = demean(m, ["lo"] + sregs, ["dt", "dh", "sym"])
    res3 = sm.OLS(dm3["lo"].values[order], dm3[sregs].values[order]).fit(
        cov_type="hac-groupsum", cov_kwds={"time": t[order], "maxlags": 14})
    srows = []
    for i, r in enumerate(sregs):
        _, s_, k = r.split("_", 2)
        b, se = res3.params[i], res3.bse[i]
        days = m[(m.sido == s_) & (m[k] > 0)]
        base = days.outsider.mean()  # 해당 유형 날의 평균 광역 외지인 → 인원 환산

        def persons(bb):
            return base * (1 - np.exp(-bb))
        srows.append(dict(sido=s_, var=k, n_days=len(days), coef=b, se=se, pval=res3.pvalues[i],
                          pct=100 * (np.exp(b) - 1), pct_lo=100 * (np.exp(b - 1.96 * se) - 1),
                          pct_hi=100 * (np.exp(b + 1.96 * se) - 1),
                          persons=persons(b), persons_lo=persons(b - 1.96 * se), persons_hi=persons(b + 1.96 * se)))
    pd.DataFrame(srows).to_csv(TAB / "sido_stay.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(srows).pivot(index="sido", columns="var", values="pct").round(2).to_string())
    ev = pd.DataFrame(erows)
    ev.to_csv(TAB / "sido_event_study.csv", index=False, encoding="utf-8-sig")
    print(ev.pivot(index="sido", columns="k", values="pct").round(2).to_string())
    pd.set_option("display.width", 200)
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
