"""핵심 차트 (PNG 300dpi, 흑백 인쇄에서도 구분되게: 제2구장은 빗금).

- fig1_event_study.png      : 정규구장 통합, 경기일 전후 ±3일 계수
- fig2_stadium_effects.png  : 구장별 경기일 외지인 방문 증가율(95% CI)
- fig3_quadrant.png         : 유입(경기당 외지인 증가) × 체류(연전 끝난 다음날 잔존 효과)
- fig4_sido_stay.png        : 대전·부산 광역 단위 연전 전날·경기일·다음날 외지인 증가(명)
- fig5_d1_lodging.png       : (보조) 구장 소재 시군구 관광소비 중 숙박 비중, 시즌 vs 비시즌 — 서술 통계
"""
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
BLUE, BLUE_LIGHT = "#2a78d6", "#a9c8ef"
plt.rcParams.update({
    "font.family": "Noto Sans KR", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlecolor": INK, "hatch.linewidth": 0.8,
})


def fig_event_study():
    d = pd.read_csv(TAB / "gameday_effect_pooled.csv")
    d = d[d.spec == "event_study"].copy()
    order = ["lead3", "lead2", "lead1", "game", "lag1", "lag2", "lag3"]
    labels = ["D-3", "D-2", "D-1", "경기일", "D+1", "D+2", "D+3"]
    d = d.set_index("var").loc[order]
    x = range(len(order))
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.axhline(0, color=INK2, lw=0.8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.vlines(x, d.pct_lo, d.pct_hi, color=INK, lw=1.4)
    ax.plot(x, d.pct, "o", ms=7, color=BLUE, mec="white", mew=1.5, zorder=3)
    g = d.loc["game"]
    ax.annotate(f"+{g.pct:.1f}%\n(95% CI {g.pct_lo:.1f}~{g.pct_hi:.1f})", (3, g.pct), xytext=(14, -6),
                textcoords="offset points", color=INK, fontsize=9, va="center")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("외지인 방문자 변화 (%)")
    ax.set_title("경기날만 늘고 전날·다음날은 0: 경기만 보고 떠난다", loc="left")
    ax.text(0, -0.2, "정규 9개 구장 통합. 같은 광역 내 비구장 도시형 시군구(군 제외) 대비, 지역×요일·공휴일, 지역×연월 고정효과. "
            "세로선=95% CI(Driscoll-Kraay).\n자료: 한국관광 데이터랩(지역별 방문자수, 이동통신), KBO 경기별 관중 기록(공개 정리본). 2023.1~2026.8",
            transform=ax.transAxes, fontsize=7, color=INK2, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "fig1_event_study.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_stadium_effects():
    d = pd.read_csv(TAB / "gameday_effect_by_stadium.csv")
    d = d[d["var"] == "game"].copy()
    d["name"] = d.stadium + " · " + d.sigungu.str.replace("창원시 ", "").str.replace("수원시 ", "")
    d.loc[d.secondary == 1, "name"] = d.name + " (제2구장)"
    d = d.sort_values(["secondary", "pct"], ascending=[False, True]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for i, r in d.iterrows():
        sec = r.secondary == 1
        ax.barh(i, r.pct, height=0.62, color=BLUE_LIGHT if sec else BLUE,
                hatch="////" if sec else None, edgecolor=BLUE if sec else "white", lw=0.6)
        ax.hlines(i, r.pct_lo, r.pct_hi, color=INK, lw=1.1)
        ax.text(max(r.pct_hi, r.pct) + 0.4, i, f"+{r.pct:.1f}%  (경기 {r.n_game_days}일)",
                va="center", fontsize=7.5, color=INK)
    ax.set_yticks(range(len(d)), d.name)
    ax.set_xlabel("홈경기일 외지인 방문자 증가율 (%, 가로선=95% CI)")
    ax.set_xlim(0, d.pct_hi.max() + 7)
    main = d[d.secondary == 0]
    top, low = main.loc[main.pct.idxmax()], main.loc[main.pct.idxmin()]
    ax.set_title(f"구장별 홈경기일 효과: {top.stadium} +{top.pct:.0f}% ~ {low.stadium} +{low.pct:.0f}%", loc="left")
    ax.text(0, -0.13, "Newey-West HAC(14일) 신뢰구간. 제2구장(빗금)은 경기 수가 적어 불확실성이 크다.\n"
            "자료: 한국관광 데이터랩(지역별 방문자수), KBO 경기별 관중 기록(공개 정리본). 2023.1~2026.8",
            transform=ax.transAxes, fontsize=7, color=INK2, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "fig2_stadium_effects.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_quadrant():
    sh = pd.read_csv(TAB / "gameday_outsider_share_of_crowd.csv")[["stadium", "extra_outsiders_per_game_point"]]
    st = pd.read_csv(TAB / "gameday_stay_by_stadium.csv")
    st = st[st["var"] == "post_only"][["stadium", "pct", "pct_lo", "pct_hi", "pval"]]
    d = sh.merge(st, on="stadium")
    d["name"] = d.stadium.str.replace("(한밭·신구장)", "", regex=False)
    d["x"] = d.extra_outsiders_per_game_point / 1000
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.axhline(0, color=INK2, lw=0.8)
    xm = d.x.median()
    ax.axvline(xm, color=GRID, lw=1, ls="--")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for r in d.itertuples():
        sig = r.pval < 0.05
        ax.vlines(r.x, r.pct_lo, r.pct_hi, color=INK, lw=1)
        ax.plot(r.x, r.pct, "o", ms=8, color=BLUE if sig else "white", mec=BLUE, mew=1.6, zorder=3)
        ax.annotate(r.name, (r.x, r.pct), xytext=(6, 4), textcoords="offset points", fontsize=8.5, color=INK)
    ax.text(0.99, 0.03, "유입↑ · 체류≈0\n→ 우선 개입 구장", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, color=INK2)
    ax.set_xlabel("유입: 경기 1회당 외지인 증가 (천 명, 2023.1~2026.8)")
    ax.set_ylabel("체류: 연전 끝난 다음날 외지인 변화 (%)")
    sig_names = d[(d.pval < 0.05) & (d.pct > 0)].name.tolist()
    extra = f" ({'·'.join(sig_names)}만 유의)" if sig_names else ""
    ax.set_title("경기날 몰려온 외지인, 다음날엔 거의 남지 않는다" + extra, loc="left")
    ax.text(0, -0.17, "점=추정치(채운 점: p<0.05), 세로선=95% CI(Newey-West). 세로 점선=유입 중앙값.\n"
            "'연전 끝난 다음날'=홈경기 다음날 중 경기가 없는 날. 자료: 한국관광 데이터랩(지역별 방문자수), KBO 경기별 관중 기록",
            transform=ax.transAxes, fontsize=7, color=INK2, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "fig3_quadrant.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_sido_stay():
    d = pd.read_csv(TAB / "sido_stay.csv")
    order = [("pre_only", "연전 전날"), ("n_games", "경기일"), ("post_only", "연전 다음날")]
    sidos = ["대전", "부산"]
    fig, axes = plt.subplots(1, 2, figsize=(6.2, 3.3), sharey=True)
    for ax, s_ in zip(axes, sidos):
        x = d[d.sido == s_].set_index("var")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for i, (v, lab) in enumerate(order):
            r = x.loc[v]
            sig = r.pval < 0.05
            ax.bar(i, r.persons / 1000, width=0.6, color=BLUE if sig else BLUE_LIGHT,
                   hatch=None if sig else "////", edgecolor=BLUE if not sig else "white", lw=0.6)
            ax.vlines(i, r.persons_lo / 1000, r.persons_hi / 1000, color=INK, lw=1.1)
            txt = f"{r.persons / 1000:+.1f}천" + ("" if sig else "\n(n.s.)")
            ax.text(i, max(r.persons_hi, 0) / 1000 + 0.3, txt, ha="center", va="bottom", fontsize=7.5, color=INK)
        ax.set_xticks(range(3), [lab for _, lab in order])
        ax.set_title(f"{s_} (광역)", loc="left", fontsize=10)
    axes[0].set_ylabel("광역 외지인 변화 (천 명)")
    fig.suptitle("구 밖 숙박까지 봐도: 대전은 전후일 변화 없음, 부산은 전날 유입 신호", x=0.01, ha="left",
                 fontsize=11, fontweight="bold", color=INK)
    fig.text(0.01, -0.06, "빗금=통계적으로 유의하지 않음(p≥0.05), 세로선=95% CI(Driscoll-Kraay). 17개 시·도 패널, 날짜·시도×요일·시도×연월 고정효과.\n"
             "자료: 한국관광 데이터랩(지역별 방문자수, 광역), KBO 경기별 관중 기록. 2023.1~2026.6",
             fontsize=7, color=INK2, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "fig4_sido_stay.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_d1_lodging():
    path = TAB / "d1_summary.csv"
    if not path.exists():  # D1(데이터랩 수동 다운로드)이 없으면 건너뛴다
        return
    d = pd.read_csv(path).sort_values("lodging_share_pct").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for i, r in d.iterrows():
        ax.hlines(i, min(r.lodging_share_season_pct, r.lodging_share_off_pct),
                  max(r.lodging_share_season_pct, r.lodging_share_off_pct), color=INK2, lw=1.2)
    ax.plot(d.lodging_share_off_pct, d.index, "o", ms=7, color="white", mec=INK2, mew=1.5, label="비시즌(1~3·10~12월)", zorder=3)
    ax.plot(d.lodging_share_season_pct, d.index, "o", ms=7, color=BLUE, mec="white", mew=1, label="시즌(4~9월)", zorder=4)
    for i, r in d.iterrows():
        ax.text(max(r.lodging_share_season_pct, r.lodging_share_off_pct) + 0.15, i, f"{r.lodging_share_pct:.1f}%",
                va="center", fontsize=7.5, color=INK)
    ax.set_yticks(d.index, d.stadium + " · " + d.sigungu.str.replace("창원시 ", "").str.replace("수원시 ", ""))
    ax.set_xlabel("관광소비 중 숙박업 비중 (%, 숫자=2025년 연간)")
    ax.set_xlim(0, d[["lodging_share_season_pct", "lodging_share_off_pct"]].max().max() + 1.2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.set_title(f"구장 소재 시군구 관광소비 중 숙박은 {d.lodging_share_pct.min():.1f}~{d.lodging_share_pct.max():.1f}%", loc="left")
    ax.text(0, -0.16, "서술 통계(보조). 월별 자료라 경기 효과와 계절성이 섞여 있어 인과로 해석하지 않는다.\n"
            "자료: 한국관광 데이터랩 빅데이터 › 신용카드 › 지역별 관광지출액, 2025.1~12, 구장 소재 시군구",
            transform=ax.transAxes, fontsize=7, color=INK2, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "fig5_d1_lodging.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig_event_study()
    fig_stadium_effects()
    fig_quadrant()
    fig_sido_stay()
    fig_d1_lodging()
