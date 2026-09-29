"""구장별 진단표 — 유입(경기당 외지인 증가) × 체류(연전 끝난 다음날 잔존 효과).

- 수치는 모두 기존 분석 표에서 읽는다 (findings.md 2·4·12·16·20·22·23번과 같은 값)
- 유형: 유입 = 경기당 외지인 증가가 9개 구장 중앙값 초과인지, 체류 = 연전 끝난 다음날 효과가 p<0.05로 양(+)인지
- 타 시도 관중 비중 = 광역 단위 '경기당 타 시·도 유입 ÷ 관중' (시군구 기준 '관중 대비 외지인 69%'와 다른 지표).
  광역 경기일 효과가 p<0.05인 곳만 쓰고, 신뢰구간 상한이 100%를 넘으면 해석할 수 없어 '오차가 커서 제외', 나머지는 '측정 불가'
- 처방 1줄은 우리 데이터(D1 숙박 비중·행정동 비중, D2 순위·연관 관광지, 우천취소 기록)에 근거한 제안이다
출력: outputs/tables/stadium_diagnosis.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "outputs" / "tables"
KEY = {"대전(한밭·신구장)": "대전"}
SIDO = {"잠실": "서울", "고척": "서울", "문학": "인천", "수원": "경기", "대전": "대전", "대구": "대구",
        "광주": "광주", "사직": "부산", "창원": "경남"}
PRESCRIPTION = {
    "잠실": "유입은 최대인데 구장은 송파구 인기 관광지 16위 → 롯데월드몰 등 송파구 상위 관광지와 경기 전후 동선을 묶는다",
    "사직": "유입 효과 최대(+11.5%)·광역 전날 유입 신호 → 전날 도착한 원정팬을 동래 숙박·경기 전 코스로 잇는다",
    "대구": "숙박 비중은 9곳 중 최고(5.5%)인데 다음날 잔존은 0 → 수성못·미술관 등 다음날 오전 코스로 체류를 늘린다",
    "대전": "다음날 잔존이 유의한 유일한 구장·타 시도 관중 비중 최대(39%) → 체류 요인을 다른 구장에 확산, 숙박 안내(비중 0.6%)를 보강한다",
    "문학": "구장 행정동 비중 3.3%로 소비가 구장 밖에 흩어짐 → 미추홀구 시장·쇼핑과 경기 전 동선을 잇는다",
    "광주": "구장이 북구 인기 관광지 1위 → 구장 방문자의 연관 관광지(광주신세계·국립아시아문화전당 등)로 동선을 넓힌다",
    "수원": "숙박 비중 9곳 중 최저(0.4%) → 방화수류정 등 장안구 인기 관광지와 숙박 안내를 묶는다",
    "고척": "돔이라 우천 취소 0회 → 날씨와 무관한 상시 연계(구로 쇼핑·문화시설)에 적합하다",
    "창원": "경기당 유입은 가장 적지만 구장 행정동(양덕2동)이 구 관광소비 1위(23.9%) → 구장 주변 상권 중심으로 체류 코스를 만든다",
}


def main():
    g = pd.read_csv(TAB / "gameday_effect_by_stadium.csv")
    g = g[(g["var"] == "game") & (g.secondary == 0)].set_index("stadium")
    sh = pd.read_csv(TAB / "gameday_outsider_share_of_crowd.csv").set_index("stadium")
    st = pd.read_csv(TAB / "gameday_stay_by_stadium.csv")
    st = st[st["var"] == "post_only"].set_index("stadium")
    sd = pd.read_csv(TAB / "sido_gameday_effect.csv").set_index("sido")
    median_extra = sh.loc[g.index, "extra_outsiders_per_game_point"].median()

    rows = []
    for s in g.sort_values("pct", ascending=False).index:
        k = KEY.get(s, s)
        extra = sh.loc[s, "extra_outsiders_per_game_point"]
        p = st.loc[s]
        stay_sig = p.pval < 0.05 and p.pct > 0
        high = extra > median_extra
        if high and not stay_sig:
            qtype = "유입↑·체류≈0 (체류 전환 우선)"
        elif high and stay_sig:
            qtype = "유입↑·체류↑ (확산 모델)"
        elif stay_sig:
            qtype = "유입 중간 이하·체류↑"
        else:
            qtype = "유입 중간 이하·체류≈0 (유입·체류 함께)"
        sido = sd.loc[SIDO[k]]
        if sido.pval < 0.05 and sido.pct_per_game > 0 and sido.share_hi <= 1.0:
            away = f"{100 * sido.share_other_sido_of_crowd:.0f}%"
            away_note = f"95% CI {100 * sido.share_lo:.0f}~{100 * sido.share_hi:.0f}%"
        elif sido.pval < 0.05 and sido.pct_per_game > 0:
            away = "오차가 커서 제외"
            away_note = f"95% CI 상한이 100%를 넘음({100 * sido.share_lo:.0f}~{100 * sido.share_hi:.0f}%)"
        else:
            away, away_note = "측정 불가", "광역 단위 효과가 유의하지 않음"
        rows.append(dict(
            stadium=k, sigungu=g.loc[s, "sigungu"],
            gameday_pct=round(g.loc[s, "pct"], 1), gameday_lo=round(g.loc[s, "pct_lo"], 1), gameday_hi=round(g.loc[s, "pct_hi"], 1),
            extra_per_game=int(round(extra, -2)),
            nextday_pct=round(p.pct, 1) + 0.0, nextday_lo=round(p.pct_lo, 1) + 0.0, nextday_hi=round(p.pct_hi, 1) + 0.0,  # -0.0 방지
            nextday_sig=bool(stay_sig), away_share=away, away_note=away_note,
            quadrant=qtype, prescription=PRESCRIPTION[k],
        ))
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "stadium_diagnosis.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    print("median extra per game:", round(median_extra))
    print(out.drop(columns=["prescription"]).to_string(index=False))


if __name__ == "__main__":
    main()
