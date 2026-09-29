"""참고자료용 분석 보고서 (HTML → PDF). 모든 수치는 outputs/tables/*.csv에서 읽는다.

  .venv/Scripts/python analysis/12_build_report.py
출력: submission/_build/report.html → submission/참고자료/01_분석보고서.pdf (Chrome 헤드리스 인쇄)
"""
import base64
import html
import importlib.util
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
OUT = ROOT / "submission" / "참고자료"
SRC = ROOT / "submission" / "_build"
_spec = importlib.util.spec_from_file_location("kl_page", Path(__file__).resolve().parent / "16_kleague_report_page.py")
kl_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kl_page)  # 12장(K리그1 확장 검증) 1쪽
CHROME = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
          Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")]


def t(name):
    return pd.read_csv(TAB / name)


def img(path, width="100%", caption=""):
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    cap = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
    return f'<figure><img src="data:image/png;base64,{b64}" style="width:{width}">{cap}</figure>'


def pct(v, d=1):
    return f"{v:+.{d}f}%"


def ci(lo, hi, d=1):
    return f"{lo:.{d}f}~{hi:.{d}f}"


def table(df, cls=""):
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>" for r in df.values)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def main():
    pooled = t("gameday_effect_pooled.csv").set_index(["spec", "var"])
    eff = t("gameday_effect_by_stadium.csv")
    game = eff[eff["var"] == "game"].set_index("stadium")
    canc = eff[eff["var"] == "canceled_only"].set_index("stadium")
    share = t("gameday_outsider_share_of_crowd.csv").set_index("stadium")
    stay = t("gameday_stay_by_stadium.csv")
    post = stay[stay["var"] == "post_only"].set_index("stadium")
    nat = t("gameday_effect_by_stadium_national_ctrl.csv").set_index("stadium")
    allc = t("gameday_effect_by_stadium_sido_allctrl.csv")
    allc = allc[allc["var"] == "game"].set_index("stadium")
    sido = t("sido_stay.csv")
    sshare = t("sido_gameday_effect.csv").set_index("sido")
    d1 = t("d1_summary.csv").set_index("stadium")
    d2 = t("d2_stadium_rank.csv").set_index("stadium")
    exp = t("expected_effect.csv")
    het = t("gameday_effect_heterogeneity.csv")

    g = pooled.loc[("pooled", "game")]
    ev = pooled.loc["event_study"]
    st_game, st_post, st_pre = (pooled.loc[("stay", v)] for v in ["game", "post_only", "pre_only"])
    c0 = pooled.loc[("pooled", "canceled_only")]
    wkd, wke = pooled.loc[("pooled_wk", "game_wkday")], pooled.loc[("pooled_wk", "game_wkend")]
    main9 = game[game.secondary == 0]
    ext = round((share.extra_outsiders_per_game_point * main9.n_game_days).sum() / main9.n_game_days.sum(), -2)
    tot_share = ((share.extra_outsiders_per_game_point * main9.n_game_days).sum()
                 / (share.mean_crowd_point * main9.n_game_days).sum())
    e_lo, e_hi = exp.iloc[0], exp.iloc[1]

    order = main9.sort_values("pct", ascending=False).index
    key = {"대전(한밭·신구장)": "대전"}
    rows = []
    for s in order:
        k = key.get(s, s)
        r, p = main9.loc[s], post.loc[s]
        rows.append([k, r.sigungu, int(r.n_game_days), f"{pct(r.pct)} ({ci(r.pct_lo, r.pct_hi)})",
                     f"{share.loc[s, 'extra_outsiders_per_game_point']:,.0f}",
                     f"{100 * share.loc[s, 'share_of_crowd_point']:.0f}%",
                     f"{pct(p.pct, 2)} ({ci(p.pct_lo, p.pct_hi, 2)})" + ("*" if p.pval < 0.05 else ""),
                     f"{int(d2.loc[k, 'rank'])}위", f"{d1.loc[k, 'lodging_share_pct']:.1f}%"])
    stadium_tbl = pd.DataFrame(rows, columns=["구장", "시군구", "경기일", "경기일 효과(95% CI)", "경기당 추가 외지인(명)",
                                              "관중 대비", "연전 다음날 효과(95% CI)", "시군구 인기관광지 순위", "숙박 비중(2025)"])
    rob = []
    for s in order:
        k = key.get(s, s)
        rob.append([k, pct(main9.loc[s, "pct"]), pct(allc.loc[s, "pct"]), pct(nat.loc[s, "pct"]),
                    pct(canc.loc[s, "pct"]) if s in canc.index else "취소 없음(돔)"])
    rob_tbl = pd.DataFrame(rob, columns=["구장", "주 설정: 광역 내 도시형 대조", "광역 전체 대조(군 포함)", "전국 대조", "우천 등 취소일"])
    ev_tbl = pd.DataFrame([[lab, f"{ev.loc[v, 'pct']:+.2f}%", ci(ev.loc[v, "pct_lo"], ev.loc[v, "pct_hi"], 2)]
                           for v, lab in zip(["lead3", "lead2", "lead1", "game", "lag1", "lag2", "lag3"],
                                             ["D-3", "D-2", "D-1", "경기일", "D+1", "D+2", "D+3"])],
                          columns=["시점", "효과", "95% CI"])
    srows = []
    for s_ in ["대전", "부산"]:
        x = sido[sido.sido == s_].set_index("var")
        for v, lab in [("pre_only", "연전 전날"), ("n_games", "경기일"), ("post_only", "연전 다음날")]:
            srows.append([s_, lab, f"{x.loc[v, 'persons']:+,.0f}명", f"{x.loc[v, 'persons_lo']:+,.0f} ~ {x.loc[v, 'persons_hi']:+,.0f}",
                          "유의" if x.loc[v, "pval"] < 0.05 else "유의하지 않음"])
    sido_tbl = pd.DataFrame(srows, columns=["광역", "시점", "광역 외지인 변화", "95% CI", "판정"])
    exp_tbl = pd.DataFrame([[r.scenario, f"{r.other_sido_share * 100:.1f}%", f"{r.annual_away_fans:,.0f}",
                             f"{r.converted_persons:,.0f}", f"{r.diff_per_trip_won / 1000:.0f}천원",
                             f"{r.expected_extra_spend_won / 1e8:,.1f}억 원"] for r in exp.itertuples()],
                           columns=["시나리오", "타 시도 관중 비중", "연간 원정 관중(명)", "숙박 전환 +1%p(명)", "1회 지출 차이", "기대효과(추정)"])
    trend = het[het["var"].isin(["game_2023", "game_2025"])].pivot(index="stadium", columns="var", values="pct")
    n_up = int((trend.game_2025 > trend.game_2023).sum())

    css = """
    @page { size: A4; margin: 16mm 15mm 16mm 15mm; }
    body { font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif; font-size: 9.2pt; line-height: 1.5; color: #111; }
    h1 { font-size: 19pt; margin: 0 0 4px; } h2 { font-size: 13pt; margin: 16px 0 6px; border-bottom: 1.5px solid #2a78d6; padding-bottom: 3px; }
    h3 { font-size: 10.5pt; margin: 10px 0 4px; } p { margin: 4px 0; } ul { margin: 4px 0; padding-left: 18px; } li { margin: 2px 0; }
    .sub { color: #52514e; margin-bottom: 10px; } .kpi { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 10px 0; }
    .kpi div { border: 1px solid #d9d8d4; border-radius: 6px; padding: 7px 9px; } .kpi b { display: block; font-size: 14pt; color: #1d5fae; }
    table { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 8pt; } th, td { border: 1px solid #d9d8d4; padding: 3px 5px; text-align: left; }
    th { background: #f1f0ec; } figure { margin: 6px 0 10px; text-align: center; page-break-inside: avoid; } figcaption { font-size: 8pt; color: #52514e; }
    .note { font-size: 8.4pt; color: #52514e; } .box { background: #f7f6f3; border-left: 3px solid #2a78d6; padding: 6px 10px; margin: 6px 0; }
    .pb { page-break-before: always; } .tag { font-weight: 700; color: #b8430f; }
    table.small td:nth-child(-n+5), table.small th:nth-child(-n+5) { white-space: nowrap; }
    """
    H = []
    H.append(f"""<h1>홈경기는 1년에 720번 열리는 축제</h1>
<p class="sub">한국관광 데이터랩으로 측정한 프로야구 경기일의 관광 효과와 9개 구장 진단 · 분석 보고서 · {date.today():%Y.%m.%d}</p>
<div class="box"><b>한 줄 요약</b> 경기일을 관광 이벤트로 측정했다. 홈경기날 구장 소재 시군구의 외지인 방문은 {pct(g.pct)}(경기당 약 {ext:,.0f}명, 관중의 약 {100 * tot_share:.0f}%) 늘지만,
경기 전날·다음날에는 0에 가깝다 — 당일치기 구조다. 9개 구장을 유입×체류로 진단해 구장별 처방을 냈고, 그 처방의 시제품으로 원정팬 체류 가이드 웹을 공개했다.</div>
<div class="kpi">
<div>홈경기일 외지인<b>{pct(g.pct)}</b>95% CI {ci(g.pct_lo, g.pct_hi)} · 9개 구장</div>
<div>경기당 추가 외지인<b>약 {ext:,.0f}명</b>관중의 약 {100 * tot_share:.0f}%</div>
<div>경기 다음날<b>{ev.loc['lag1', 'pct']:+.2f}%</b>전날 {ev.loc['lead1', 'pct']:+.2f}% · 0과 구분 안 됨</div>
<div>구장 소재 시군구 숙박 비중<b>{d1.lodging_share_pct.min():.1f}~{d1.lodging_share_pct.max():.1f}%</b>관광소비 중(2025)</div>
<div>구장의 지역 위상<b>9곳 중 {int((d2['rank'] <= 7).sum())}곳</b>시군구 인기 관광지 7위 안</div>
<div><span class="tag">기대효과(추정)</span><b>연 {e_lo.expected_extra_spend_won / 1e8:.0f}억~{e_hi.expected_extra_spend_won / 1e8:.0f}억 원</b>숙박 전환 +1%p 가정</div>
</div>""")

    H.append("""<h2>1. 배경과 질문 — 측정되지 않던 경기일</h2>
<ul><li>프로야구 정규시즌 관중은 2023년 8,100,326명 → 2024년 10,887,705명 → 2025년 12,312,519명(KBO 경기별 관중 기록 합계, 공식 발표와 일치). 한 시즌 720경기가 9개 구장에서 거의 매일 열린다.</li>
<li>그러나 관중 수 외에 경기가 구장 소재 지역에 외지인을 얼마나 데려오고, 그들이 머무는지를 보여 주는 공개 지표는 찾기 어렵다. 측정이 없으니 구장마다 유입과 체류 중 무엇을 늘릴지 판단할 근거도 없다.</li>
<li>질문 ① 홈경기는 구장 소재 시군구의 외지인을 얼마나 늘리는가(유입) ② 늘어난 외지인은 전날·다음날까지 머무는가(체류) ③ 구장별로 무엇을 해야 하는가(진단) ④ 체류로 바꾸면 얼마의 관광지출이 생기는가(기대효과)</li></ul>""")

    data_tbl = pd.DataFrame([
        ["데이터랩 빅데이터 › 이동통신 › 지역별 방문자수", "시군구·광역 × 일, 현지인/외지인/외국인", "2023.1.1~2026.8.29", "유입·체류 측정(메인). 공공데이터포털 API(15101972)로 전국 247개 시군구 수집, 호출 67회"],
        ["데이터랩 빅데이터 › 신용카드 › 지역별 관광지출액", "구장 소재 9개 시군구 × 월, 업종·행정동", "2025.1~12", "업종 구성·숙박 비중(서술 통계)"],
        ["데이터랩 지역별 분석 › 중심-연관 관광지 지도", "구장 소재 9개 시군구", "2025.9~2026.8", "구장 위상(순위), 웹 코스 후보"],
        ["데이터랩 관광통계 › 국민여행조사", "2025 보고서(분석편) [표 8]", "2025", "숙박·당일 1회 평균 지출(기대효과 산식)"],
        ["KBO 경기별 관중 기록(공개 정리본)", "경기별 날짜·구장·관중·취소", "2023~2026.9", "처치 변수. 2023~2025 시즌 총관중이 공식치와 1명 단위 일치"],
        ["한국어 위키백과 'K리그1의 경기 결과'(CC BY-SA)", "경기별 날짜·경기장·관중", "2024~2025", "11장 확장 검증(K리그1). 누적 관중을 연맹 발표와 대조"],
        ["한국관광공사 TourAPI(국문 관광정보)", "구장 반경 관광지·음식점·숙박", "2026.9 조회", "웹 코스 실장소 195곳"],
    ], columns=["자료", "단위", "기간", "용도"])
    H.append("<h2>2. 데이터</h2>" + table(data_tbl) +
             "<p class='note'>데이터랩 웹사이트는 크롤링하지 않았다(수동 다운로드·공식 API만 사용). '외지인'은 해당 시군구 비거주 방문자(같은 시 다른 구 주민 포함), 광역 외지인은 해당 시·도 비거주 방문자다.</p>")

    H.append(f"""<h2>3. 분석 방법</h2>
<ul><li><b>비교 설계(시군구 × 일)</b>: 구장 시군구의 log(외지인)에서 같은 광역의 구장 없는 <b>도시형</b> 시군구(자치구·시·일반구, 군 제외) 평균을 뺀 값(= 광역×날짜 고정효과)을 종속변수로, 지역×(요일×공휴일)·지역×연월 고정효과와 우천 등 취소일 더미를 통제. 포스트시즌 기간(정규시즌 종료~11/30)은 제외.</li>
<li><b>군 제외 이유</b>: 섬·농촌 군(예: 인천 강화·옹진)은 비 오는 날 방문이 크게 줄어 우천일에 가짜 차이를 만든다. 모든 구장에 같은 규칙을 적용했고, 광역 전체 대조 결과를 강건성으로 제시(7장).</li>
<li><b>이벤트 스터디(체류)</b>: 경기일 전후 D-3~D+3 분포시차, 연전 경계일(연전 끝난 다음날·시작 전날, 경기 없는 날) 더미. 구 밖 숙박 가능성은 17개 시·도 패널(날짜·시도×요일·시도×연월 고정효과)로 대전·부산을 점검.</li>
<li><b>우천취소 검증</b>: 편성됐지만 열리지 않은 날을 별도 더미로 두어, 일정·요일이 아닌 경기 자체의 효과를 분리.</li>
<li><b>관중 대비 외지인 비율</b>: 경기일 외지인 증가분 ÷ 관중. 광역 단위로는 경기당 타 시·도 유입 ÷ 관중(타 시도 관중 비중 — 시군구 기준 관중 대비 외지인 비율과 다른 지표).</li>
<li><b>구장별 진단</b>: 경기당 외지인 증가가 9개 구장 중앙값 초과면 '유입↑', 연전 끝난 다음날 효과가 p&lt;0.05로 양(+)이면 '체류↑'.</li>
<li><b>표준오차</b>: 구장별은 처치 지역이 1곳이라 지역 클러스터가 불가능 → Newey-West HAC(14일). 통합·광역은 Driscoll-Kraay(시간 HAC + 지역 간 상관 허용).</li>
<li><b>효과(%)</b> = 100×(e<sup>β</sup>−1). 경기당 추가 외지인 = Σ경기일 외지인×(1−e<sup>−β</sup>) ÷ 경기일 수.</li>
<li><b>D1 관광지출</b>은 월별 자료라 계절성이 섞여 있어 <b>서술 통계로만</b> 쓰고 인과로 해석하지 않는다.</li></ul>""")

    H.append(f"""<h2>4. 결과 ① 유입 — 홈경기날 외지인 {pct(g.pct)}</h2>
<ul><li>정규 9개 구장 통합 {pct(g.pct)} (95% CI {ci(g.pct_lo, g.pct_hi)}), 경기일 {int(main9.n_game_days.sum()):,}일. 9곳 모두 p&lt;0.001. 경기당 약 {ext:,.0f}명, 관중의 약 {100 * tot_share:.0f}%.</li>
<li>평일 {pct(wkd.pct)} vs 주말·공휴일 {pct(wke.pct)} — 평일 야간경기도 비슷하게 끌어온다. {n_up}곳 모두 2023년보다 2025년 효과가 크다.</li></ul>""")
    H.append(img(FIG / "fig2_stadium_effects.png", "62%", "그림 1. 구장별 홈경기일 외지인 방문 증가율(95% CI). 제2구장(빗금)은 경기 수가 적다."))

    H.append(f"""<h2>5. 결과 ② 체류 — 경기만 보고 떠난다</h2>
<ul><li>이벤트 스터디: 경기일 {ev.loc['game', 'pct']:+.2f}%, 전날 {ev.loc['lead1', 'pct']:+.2f}%, 다음날 {ev.loc['lag1', 'pct']:+.2f}% — 전후 사흘 모두 ±0.3% 이내.</li>
<li>연전 끝난 다음날(경기 없는 날) {st_post.pct:+.2f}% (95% CI {ci(st_post.pct_lo, st_post.pct_hi, 2)}), 시작 전날 {st_pre.pct:+.2f}% → 경기일 증가분({pct(st_game.pct)})의 약 {100 * st_post.pct / st_game.pct:.1f}%만 다음날까지 남는다.</li>
<li>구장별로는 대전만 연전 다음날 효과가 유의(표의 *). 광역으로 넓혀도 대전은 다음날 변화가 없고, 부산만 연전 전날 유입 신호가 있다.</li></ul>""")
    H.append(img(FIG / "fig1_event_study.png", "64%", "그림 2. 경기 전후 외지인 변화(정규 9개 구장 통합, 95% CI)"))
    H.append(table(ev_tbl))
    H.append(img(FIG / "fig4_sido_stay.png", "64%", "그림 3. 광역 단위 점검: 대전·부산 연전 전날·경기일·다음날 외지인 변화(명)"))
    H.append(table(sido_tbl) + f"<p class='note'>광역 외지인 기저가 하루 20만~40만 명대라 신뢰구간이 넓다. 타 시도 관중 비중(경기당 광역 외지인 증가 ÷ 관중): 부산 {100 * sshare.loc['부산', 'share_other_sido_of_crowd']:.1f}%, 대전 {100 * sshare.loc['대전', 'share_other_sido_of_crowd']:.1f}%.</p>")

    dg = pd.read_csv(TAB / "stadium_diagnosis.csv")
    diag_tbl = pd.DataFrame([[r.stadium, f"{r.gameday_pct:+.1f}%", f"약 {r.extra_per_game:,}명",
                              f"{r.nextday_pct:+.1f}%" + (" (유의)" if r.nextday_sig else ""),
                              r.away_share, r.quadrant, r.prescription] for r in dg.itertuples()],
                            columns=["구장", "경기일 효과", "경기당 외지인", "다음날 잔존", "타 시도 관중 비중", "유형", "처방(제안)"])
    H.append("""<h2>6. 구장별 진단 — 유입 × 체류</h2>
<ul><li>유입↑·체류≈0(사직·대구·잠실): 외지인은 많이 오지만 다음날 남지 않는다 → 체류 전환이 우선이다.</li>
<li>유입↑·체류↑(대전): 다음날 잔존이 유의한 유일한 구장 → 체류 요인을 다른 구장에 확산할 모델이다.</li>
<li>유입 중간 이하·체류≈0(문학·수원·광주·고척·창원): 유입과 체류를 함께 늘려야 한다.</li></ul>""")
    H.append(img(FIG / "fig3_quadrant.png", "62%", "그림 4. 유입(경기당 외지인 증가) × 체류(연전 끝난 다음날 효과) 사분면"))
    H.append(table(diag_tbl, "small") + "<p class='note'>타 시도 관중 비중: 광역 단위 경기당 타 시·도 유입 ÷ 관중(광역 효과가 유의하지 않으면 '측정 불가'; 창원(경남)은 신뢰구간 상한이 100%를 넘어(26~111%) 해석할 수 없어 '오차가 커서 제외'). 처방은 분석 결과(숙박 비중·데이터랩 순위·우천취소 기록 등)에 근거한 제안이다.</p>")

    H.append(f"""<h2>7. 보조 — 관광지출(D1)과 구장 위상(D2)</h2>
<ul><li>구장 소재 시군구 관광소비 중 숙박 {d1.lodging_share_pct.min():.1f}~{d1.lodging_share_pct.max():.1f}%(중앙값 {d1.lodging_share_pct.median():.1f}%). 시즌(4~9월) 월평균 소비는 비시즌과 {d1.season_vs_off_pct.min():+.1f}~{d1.season_vs_off_pct.max():+.1f}%로 차이가 거의 없다(계절성 포함, 인과 아님).</li>
<li>구장 소재 행정동이 시군구 관광소비에서 차지하는 비중은 대부분 한 자릿수(잠실2동 {d1.loc['잠실', 'stadium_dong_share_pct']:.1f}%, 임동 {d1.loc['광주', 'stadium_dong_share_pct']:.1f}%). 예외: 창원 양덕2동 {d1.loc['창원', 'stadium_dong_share_pct']:.1f}%.</li>
<li>구장은 이미 지역 대표 관광지: 시군구 중심관광지 순위 광주 1위, 대전 2위, 고척 3위, 대구·사직 4위, 수원·창원(마산야구장 표기) 5위, 문학 7위, 잠실 16위.</li></ul>""")
    H.append(img(FIG / "fig5_d1_lodging.png", "60%", "그림 5. 구장 소재 시군구 관광소비 중 숙박 비중(시즌 vs 비시즌, 서술 통계)"))

    H.append("<h2>8. 강건성</h2>" + table(rob_tbl) +
             f"<p class='note'>통합 기준 취소일 효과 {pct(c0.pct)}(경기일의 약 {100 * c0.pct / g.pct:.0f}%) — 취소 결정 전에 이미 이동한 관중이거나 경기와 함께 잡아 둔 일정일 수 있다. 취소일 효과가 경기일보다 작아 경기 자체가 유입의 원인이라는 해석을 지지한다. 서울 구장은 전국 대조로 바꾸면 작아진다.</p>")

    H.append(f"""<h2>9. 기대효과(추정)</h2>
<div class="box"><span class="tag">기대효과(추정)</span> 연간 추가 관광지출 = 2025 관중 × 타 시도 관중 비중 × 숙박 전환 +1%p × (숙박여행 1회 평균 지출 − 당일여행 1회 평균 지출)</div>
<ul><li>2025 관중 {int(e_lo.crowd_2025):,}명(KBO 경기별 관중 기록). 타 시도 관중 비중 부산 {100 * e_lo.other_sido_share:.1f}%(하한)~대전 {100 * e_hi.other_sido_share:.1f}%(상한)을 전 구장에 적용한 <b>가정</b>.</li>
<li>1회 평균 지출: 2025 국민여행조사 보고서(분석편) [표 8] 1회 평균 여행 지출액(6쪽) — 국내 숙박여행 221천원, 당일여행 69천원, 차이 152천원(여행 경험자 1인·1회 기준). 교차 확인 [표 2-1-24](72쪽), 여행지별 [표 2-1-25](73쪽).</li>
<li>숙박 전환 +1%p는 관측값이 아닌 목표 가정이다.</li></ul>""" + table(exp_tbl))

    H.append("<h2>10. 처방의 시제품과 방법 공개</h2>"
             "<ul><li><b>구장별 진단표 공개</b>: 웹 상단에 9개 구장의 경기일 효과·경기당 외지인·다음날 잔존·타 시도 관중 비중·유형·처방을 지자체·구단 담당자용으로 싣는다.</li>"
             "<li><b>원정팬 체류 가이드</b>: 진단의 처방('당일치기를 하룻밤으로')을 옮긴 시제품. 9개 구장 × 경기 전(데이터랩 연관·인기 관광지 + TourAPI) · 경기 후 · 하룻밤(데이터랩 인기 숙소 + TourAPI 숙박), 장소 285곳. 미확인 영업시간·가격은 싣지 않는다.</li>"
             "<li><b>코드와 방법 공개(GitHub)</b>: 경기 일정 표만 바꾸면 K리그·농구·배구, 지역 축제·공연에 같은 측정을 그대로 재사용할 수 있다. 11장에서 K리그1에 실제로 적용해 확인했다.</li></ul>")
    H.append(img(OUT / "04_웹화면" / "04_웹화면_모바일_진단.png", "26%", "그림 6. 웹 상단의 구장별 진단(모바일)"))

    H.append(kl_page.section_html())  # 11. 확장 검증 — K리그1 (새 쪽에서 시작하는 1쪽)
    css += kl_page.KL_CSS

    H.append("""<h2 class="pb">12. 한계와 재현</h2>
<ul><li>이동통신 '방문자'는 일상생활권 밖 체류자 기준이며 관광 목적을 알 수 없다. 시군구 '외지인'에는 같은 시 다른 구 주민이 포함된다.</li>
<li>포스트시즌 경기일 정보가 없어 해당 기간은 제외했다. 방문자 데이터는 2026.8.29까지라 2026 가을야구는 관측하지 못했다.</li>
<li>광역 분석은 기저 규모가 커 대전·부산만 식별됐다. 기대효과는 가정(타 시도 관중 비중 전 구장 적용, 숙박 전환 +1%p)에 의존한다.</li>
<li>재현: <code>.venv/Scripts/python analysis/run_all.py</code> 한 번으로 수집(캐시)·분석·그림·웹 데이터까지 생성. 데이터랩 수동 자료는 data/raw/datalab/에 두고 00_organize_datalab.py로 정리.</li></ul>""")


    SRC.mkdir(parents=True, exist_ok=True)
    doc = f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>분석 보고서</title><style>{css}</style></head><body>{''.join(H)}</body></html>"
    src = SRC / "report.html"
    src.write_text(doc, encoding="utf-8")
    chrome = next(p for p in CHROME if p.exists())
    pdf = OUT / "01_분석보고서.pdf"
    subprocess.run([str(chrome), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={SRC / '.chrome'}", f"--print-to-pdf={pdf}", src.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    from pypdf import PdfReader
    print("pages:", len(PdfReader(str(pdf)).pages), pdf)


if __name__ == "__main__":
    main()
