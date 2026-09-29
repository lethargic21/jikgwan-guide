"""분석 보고서 11장(1쪽): '확장 검증 — 같은 방법을 K리그1에 적용'.

- section_html(), KL_CSS: 12_build_report.py가 본 보고서 마지막 쪽으로 붙인다(8쪽).
- 단독 실행하면 이 쪽만 따로 확인용으로 만든다:
  .venv/Scripts/python analysis/16_kleague_report_page.py → outputs/drafts/보고서_추가쪽_K리그1_초안.html, .pdf
모든 수치는 outputs/tables/kleague_*.csv, gameday_*.csv에서 읽는다.
"""
import base64
import html
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
OUT = ROOT / "outputs" / "drafts"
CHROME = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
          Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")]
BASE_CSS = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
body { font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif; font-size: 9.2pt; line-height: 1.5; color: #111; }
h2 { font-size: 13pt; margin: 16px 0 6px; border-bottom: 1.5px solid #2a78d6; padding-bottom: 3px; }
p { margin: 4px 0; } ul { margin: 4px 0; padding-left: 18px; } li { margin: 2px 0; }
.kpi { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 10px 0; }
.kpi div { border: 1px solid #d9d8d4; border-radius: 6px; padding: 7px 9px; } .kpi b { display: block; font-size: 14pt; color: #1d5fae; }
table { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 8pt; } th, td { border: 1px solid #d9d8d4; padding: 3px 5px; text-align: left; }
th { background: #f1f0ec; } figure { margin: 6px 0 10px; text-align: center; } figcaption { font-size: 8pt; color: #52514e; }
.note { font-size: 8.4pt; color: #52514e; } .box { background: #f7f6f3; border-left: 3px solid #2a78d6; padding: 6px 10px; margin: 6px 0; }
.pb { page-break-before: always; }
"""
# 11장 전용(본 보고서 스타일 위에 덮어쓴다. .kl 안에만 적용)
KL_CSS = """
.kl h2 { margin-top: 0; } .kl .kpi { margin: 8px 0; } .kl .kpi div { padding: 6px 9px; } .kl .kpi b { font-size: 13pt; }
.kl table { font-size: 7.8pt; } .kl th, .kl td { padding: 2px 5px; } .kl td { white-space: nowrap; }
.kl figure { margin: 4px 0 6px; } .kl .note { font-size: 8pt; } .kl .box { padding: 5px 10px; }
.kl .two { display: grid; grid-template-columns: 1.05fr 1fr; gap: 10px; align-items: start; }
"""


def img(path, width, caption):
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b64}" style="width:{width}"><figcaption>{html.escape(caption)}</figcaption></figure>'


def table(df):
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>" for r in df.values)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def section_html():
    kp = pd.read_csv(TAB / "kleague_effect_pooled.csv").set_index(["spec", "var"])
    kb = pd.read_csv(TAB / "kleague_effect_by_stadium.csv")
    kv = pd.read_csv(TAB / "kleague_validation.csv")
    g = kp.loc[("pooled", "kl_game")]
    ev = kp.loc["event_study"]
    wkd, wke = kp.loc[("pooled_wk", "kl_wkday")], kp.loc[("pooled_wk", "kl_wkend")]
    sm_, mt = kp.loc[("pooled_city", "kl_small")], kp.loc[("pooled_city", "kl_metro")]
    nk, ok = kp.loc[("pooled_kbo_overlap", "kl_game_nokbo")], kp.loc[("pooled_kbo_overlap", "kl_game_kbo")]
    k_ext = round(g.extra_outsiders_per_game_point, -2)
    k_share = g.extra_outsiders_per_game_point / g.mean_crowd

    # KBO 비교값(본 보고서와 같은 계산)
    bp = pd.read_csv(TAB / "gameday_effect_pooled.csv").set_index(["spec", "var"])
    b = bp.loc[("pooled", "game")]
    bev = bp.loc["event_study"]
    eff = pd.read_csv(TAB / "gameday_effect_by_stadium.csv")
    main9 = eff[(eff["var"] == "game") & (eff.secondary == 0)].set_index("stadium")
    share = pd.read_csv(TAB / "gameday_outsider_share_of_crowd.csv").set_index("stadium")
    b_ext = round((share.extra_outsiders_per_game_point * main9.n_game_days).sum() / main9.n_game_days.sum(), -2)
    b_share = ((share.extra_outsiders_per_game_point * main9.n_game_days).sum()
               / (share.mean_crowd_point * main9.n_game_days).sum())

    v25 = kv[kv.season == 2025].iloc[0]
    n_sig = int((kb.pval < 0.05).sum())
    rows = []
    for r in kb.itertuples():
        mark = "" if r.pval < 0.05 else " (유의X)"
        rows.append([r.sigungu, r.venues.replace("/", "·"), r.years, int(r.n_game_days), f"{r.mean_crowd:,.0f}",
                     f"{r.pct:+.1f}% ({r.pct_lo:.1f}~{r.pct_hi:.1f}){mark}", f"{r.extra_outsiders_per_game_point:,.0f}"])
    st_tbl = pd.DataFrame(rows, columns=["시군구", "경기장", "연도", "경기일", "평균 관중", "경기일 효과(95% CI)", "경기당 외지인"])
    cmp_tbl = pd.DataFrame([
        ["경기일 외지인", f"{b.pct:+.1f}% ({b.pct_lo:.1f}~{b.pct_hi:.1f})", f"{g.pct:+.1f}% ({g.pct_lo:.1f}~{g.pct_hi:.1f})"],
        ["경기당 추가 외지인", f"약 {b_ext:,.0f}명", f"약 {k_ext:,.0f}명"],
        ["관중 대비 외지인 비율", f"약 {100 * b_share:.0f}%", f"약 {100 * k_share:.0f}%"],
        ["전날 / 다음날", f"{bev.loc['lead1', 'pct']:+.2f}% / {bev.loc['lag1', 'pct']:+.2f}%",
         f"{ev.loc['lead1', 'pct']:+.2f}% / {ev.loc['lag1', 'pct']:+.2f}%"],
        ["범위", "정규 9개 구장, 2023.1~2026.8", f"{int(g.n_units)}개 경기장 시군구, 2024~2025"],
    ], columns=["", "KBO(프로야구, 본 분석)", "K리그1(확장)"])

    H = [f"""<section class="kl pb"><h2>11. 확장 검증 — 같은 방법을 K리그1에 적용</h2>
<div class="box"><b>요약</b> 코드와 설계는 그대로 두고 경기 일정 표만 K리그1(2024~2025)로 바꿨다. 홈경기날 경기장 소재 시군구의 외지인은
{g.pct:+.1f}%(95% CI {g.pct_lo:.1f}~{g.pct_hi:.1f}) 늘고 전날·다음날은 0과 구분되지 않는다 — 프로야구와 같은 당일치기 구조가 종목을 바꿔도 재현된다.</div>
<div class="kpi">
<div>K리그1 홈경기일 외지인<b>{g.pct:+.1f}%</b>95% CI {g.pct_lo:.1f}~{g.pct_hi:.1f} · {int(g.n_units)}개 시군구</div>
<div>경기당 추가 외지인<b>약 {k_ext:,.0f}명</b>관중의 약 {100 * k_share:.0f}% (KBO 약 {100 * b_share:.0f}%)</div>
<div>전날 / 다음날<b>{ev.loc['lead1', 'pct']:+.2f}% / {ev.loc['lag1', 'pct']:+.2f}%</b>0과 구분 안 됨</div>
</div>
<div class="two"><div>
<ul><li><b>데이터</b>: 방문자는 본 분석의 데이터랩 캐시(추가 API 호출 0회). 경기는 한국어 위키백과 'K리그1의 경기 결과'(CC BY-SA) 정규 456경기와 K리그1 구장 승강 PO 3경기, 경기장→시군구는 경기장 문서 주소(16곳).</li>
<li><b>검증</b>: 시즌별 228경기·12팀. 2025 정규 33라운드 종료 누적 관중 {v25.official_check.split(': ', 1)[1]}.</li>
<li><b>설계</b>: KBO 분석과 동일(같은 광역의 경기장 없는 도시형 시군구 대비, 지역×요일·공휴일·연월 고정효과, Driscoll-Kraay). KBO 구장과 같은 시군구 3곳(수원 장안구·울산 남구·포항 남구)은 KBO 경기일 통제, K리그2 시즌(안양 2024·인천 2025)은 제외.</li>
<li><b>결과</b>: {len(kb)}곳 중 {n_sig}곳 p&lt;0.05. 평일 {wkd.pct:+.1f}% · 주말 {wke.pct:+.1f}%. 소도시(김천·춘천·강릉·서귀포) {sm_.pct:+.1f}% vs 구 단위 {mt.pct:+.1f}%. KBO와 겹치지 않는 11곳만 {nk.pct:+.1f}%({nk.pct_lo:.1f}~{nk.pct_hi:.1f}).</li></ul>
</div><div>{img(FIG / "fig6_kleague_event_study.png", "100%", f"그림 7. K리그1 경기 전후 외지인 변화(95% CI). 경기일 계수는 전후 시차를 함께 넣은 모형 값({ev.loc['kl_game', 'pct']:+.1f}%).")}</div></div>
{table(cmp_tbl)}
{table(st_tbl)}
<p class="note"><b>의미</b>: 경기 일정 표(날짜·경기장)만 있으면 같은 코드로 다른 종목의 '경기일 관광 효과'를 잴 수 있다 — 농구·배구, 지역 축제·공연으로 확산할 수 있는 근거.
<b>한계</b>: ACL·코리아컵·콘서트 등 다른 행사일은 비경기일로 처리해 효과를 작게 잡을 수 있다. K리그2 경기장 시군구는 대조군에 남았다. 관중 수는 위키백과 값(공식 누적 관중과 −0.01% 차이)이며, 효과 추정은 홈경기 여부만 쓴다.
강릉·서귀포처럼 평소 외지인이 많은 관광도시는 %가 작게 잡힐 수 있다(가설). 재현: <code>analysis/14_fetch_kleague.py</code> → <code>15_kleague_extension.py</code>.</p></section>"""]
    return "".join(H)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    body = section_html().replace('class="kl pb"', 'class="kl"')
    doc = f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>확장 검증 K리그1</title><style>{BASE_CSS}{KL_CSS}</style></head><body>{body}</body></html>"
    src = OUT / "보고서_추가쪽_K리그1_초안.html"
    src.write_text(doc, encoding="utf-8")
    pdf = OUT / "보고서_추가쪽_K리그1_초안.pdf"
    chrome = next(p for p in CHROME if p.exists())
    build = ROOT / "submission" / "_build"
    build.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(chrome), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={build / '.chrome'}", f"--print-to-pdf={pdf}", src.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    from pypdf import PdfReader
    print("pages:", len(PdfReader(str(pdf)).pages), pdf)


if __name__ == "__main__":
    main()
