"""기대효과(추정) — 원정 관중의 숙박 전환 +1%p 시 추가 관광지출.

산식 (CLAUDE.md §6-C):
  연간 원정 관중 = 2025 정규시즌 관중 × 타 시·도 유입 비율
  추가 지출 = 연간 원정 관중 × 숙박 전환 +1%p × (숙박여행 1회 평균 지출 − 당일여행 1회 평균 지출)

입력과 출처
- 2025 관중: KBO 경기별 관중 기록 합계 12,312,519명 (공식 발표와 일치, data/raw/kbo/SOURCE.md)
- 타 시·도 유입 비율: 광역 보조분석(outputs/tables/sido_gameday_effect.csv)의 부산·대전 값 → 범위로 쓴다(전 구장 적용은 가정)
- 1회 평균 지출: 2025 국민여행조사 보고서(분석편) [표 8] 1회 평균 여행 지출액, 보고서 6쪽(PDF 26쪽)
  '여행 경험자' 기준 1인이 여행 1회에 쓴 금액(천원). 교차 확인: [표 2-1-24] 72쪽(PDF 103쪽)
  여행지별 값: [표 2-1-25] 73쪽(PDF 104쪽) → 민감도 분석
출력: data/processed/nts2025_per_trip_spend.csv, outputs/tables/expected_effect.csv
"""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "datalab" / "2025_국민여행조사_보고서_-분석편-.pdf"
TAB = ROOT / "outputs" / "tables"
PROC = ROOT / "data" / "processed"
CONVERSION = 0.01  # 숙박 전환 +1%p


def read_pdf_tables():
    with pdfplumber.open(PDF) as pdf:
        p26 = pdf.pages[25].extract_text()
        p103 = pdf.pages[102].extract_text()
        p104 = pdf.pages[103].extract_text()
    # [표 8] (PDF 26쪽): '숙박 192 207 215 215 221 ...' — 국내여행 21~25년이 앞 5개
    t8 = p26[p26.index("[ 표 8 ]"):]
    stay = [int(x) for x in re.search(r"\n숙박 ([\d ]+)", t8).group(1).split()]
    day = [int(x) for x in re.search(r"\n당일 ([\d ]+)", t8).group(1).split()]
    assert "1회 평균 여행 지출액" in t8 and "(단위 : 천원)" in t8
    nat = dict(stay=stay[4], day=day[4])
    # [표 2-1-24] (PDF 103쪽) 전체 행: '전체 133 221 69 ...'로 교차 확인
    r = [int(x) for x in re.search(r"\n전체 ([\d ]+)", p103[p103.index("[ 표 2-1-24 ]"):]).group(1).split()]
    assert (r[1], r[2]) == (nat["stay"], nat["day"]), (r, nat)
    # [표 2-1-25] (PDF 104쪽) 여행지별: '부산 179 244 84 ...'
    dest = {}
    for name in ["서울", "부산", "대구", "인천", "광주", "대전", "경기", "경남"]:
        m = re.search(rf"\n{name} (\d+) (\d+) (\d+)", p104)
        dest[name] = dict(stay=int(m.group(2)), day=int(m.group(3)))
    return nat, dest


def main():
    nat, dest = read_pdf_tables()
    rows = [dict(scope="전국", stay_k=nat["stay"], day_k=nat["day"],
                 source="2025 국민여행조사 보고서(분석편) [표 8] 1회 평균 여행 지출액, 6쪽(PDF 26쪽)")]
    rows += [dict(scope=k, stay_k=v["stay"], day_k=v["day"],
                  source="같은 보고서 [표 2-1-25] 여행지별 1회 평균 여행 지출액, 73쪽(PDF 104쪽)") for k, v in dest.items()]
    spend = pd.DataFrame(rows).assign(diff_k=lambda d: d.stay_k - d.day_k,
                                      unit="천원, 여행 경험자 1인의 여행 1회 기준")
    spend.to_csv(PROC / "nts2025_per_trip_spend.csv", index=False, encoding="utf-8-sig")

    crowd = int(pd.read_csv(ROOT / "data" / "raw" / "kbo" / "games.csv").query("season == 2025").crowd.sum())
    sido = pd.read_csv(TAB / "sido_gameday_effect.csv").set_index("sido")
    shares = {"부산(하한)": sido.loc["부산", "share_other_sido_of_crowd"],
              "대전(상한)": sido.loc["대전", "share_other_sido_of_crowd"]}
    diff_won = (nat["stay"] - nat["day"]) * 1000
    out = []
    for label, sh in shares.items():
        visitors = crowd * sh
        converted = visitors * CONVERSION
        out.append(dict(scenario=label, crowd_2025=crowd, other_sido_share=sh, annual_away_fans=visitors,
                        conversion=CONVERSION, converted_persons=converted, diff_per_trip_won=diff_won,
                        expected_extra_spend_won=converted * diff_won,
                        label="기대효과(추정)"))
    # 민감도: 부산·대전 각자의 여행지별 지출 차이를 쓰면
    for label, key, sh in [("부산 여행지별 차이", "부산", shares["부산(하한)"]), ("대전 여행지별 차이", "대전", shares["대전(상한)"])]:
        d = (dest[key]["stay"] - dest[key]["day"]) * 1000
        converted = crowd * sh * CONVERSION
        out.append(dict(scenario=f"민감도: {label}", crowd_2025=crowd, other_sido_share=sh, annual_away_fans=crowd * sh,
                        conversion=CONVERSION, converted_persons=converted, diff_per_trip_won=d,
                        expected_extra_spend_won=converted * d, label="기대효과(추정)"))
    res = pd.DataFrame(out)
    res.to_csv(TAB / "expected_effect.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 220)
    print(spend.to_string(index=False))
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
