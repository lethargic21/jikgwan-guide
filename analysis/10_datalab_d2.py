"""D2 중심-연관 관광지 (데이터랩 지역별 분석, 2025-09~2026-08) 정리.

- 구장이 소재 시군구 '중심관광지' 순위에서 몇 위인지 → outputs/tables/d2_stadium_rank.csv
- 가이드 웹 '경기 전 코스'용 데이터랩 인기 관광지 → data/processed/datalab_pre_course.csv
- 가이드 웹 '하룻밤'용 데이터랩 인기 숙박(숙박 분류) → data/processed/datalab_stay.csv
  - 구장을 중심으로 받은 연관관광지가 있으면(현재 광주) 그 순위를, 없으면 시군구 중심관광지 순위를 쓴다
  - 숙박·기타관광(역·터미널)과 구장 자체는 뺀다
※ 이름·분류·순위만 쓴다(영업시간 등 미확인 정보 없음, §3-6)
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D2 = ROOT / "data" / "raw" / "datalab" / "D2"
TAB = ROOT / "outputs" / "tables"
PROC = ROOT / "data" / "processed"
# 구장 POI 이름 (데이터랩 표기). 창원은 목록에 '창원NC파크'가 없고 '마산야구장'이 있다
STADIUM_POI = {"잠실": "잠실야구장", "고척": "고척스카이돔", "문학": "인천SSG랜더스필드", "수원": "수원KT위즈파크",
               "대전": "대전한화생명볼파크", "대구": "대구삼성라이온즈파크", "광주": "광주기아챔피언스필드",
               "사직": "사직야구장", "창원": "마산야구장"}
EXCLUDE_CAT = {"숙박", "기타관광"}
N = 6
N_STAY = 4


def main():
    ranks, courses, stays = [], [], []
    for st, poi in STADIUM_POI.items():
        cf = next(D2.glob(f"{st}_*_중심관광지.csv"))
        c = pd.read_csv(cf)
        hit = c[c["중심관광지명"] == poi]
        ranks.append(dict(stadium=st, sigungu=c["중심시군구명"].iloc[0], poi=poi,
                          rank=int(hit["순위"].iloc[0]) if len(hit) else None, n_listed=len(c)))
        related = list(D2.glob(f"{st}_*_연관관광지_중심={poi}.csv"))
        if related:
            r = pd.read_csv(related[0])
            r = r[~r["구분"].isin(EXCLUDE_CAT) & (r["연관관광지명"] != poi)]
            for x in r.head(N).itertuples():
                courses.append(dict(stadium=st, source="related", rank=x.순위, title=x.연관관광지명,
                                    cat=x.구분, sigungu=x.연관관광지시군구명))
            rs = pd.read_csv(related[0])
            for x in rs[rs["구분"] == "숙박"].head(N_STAY).itertuples():
                stays.append(dict(stadium=st, source="related", rank=x.순위, title=x.연관관광지명,
                                  sigungu=x.연관관광지시군구명))
        else:
            k = c[~c["중심카테고리 명_중"].isin(EXCLUDE_CAT) & (c["중심관광지명"] != poi)]
            for x in k.head(N).itertuples():
                courses.append(dict(stadium=st, source="central", rank=x.순위, title=x.중심관광지명,
                                    cat=x._6, sigungu=x.중심시군구명))
            for x in c[c["중심카테고리 명_중"] == "숙박"].head(N_STAY).itertuples():
                stays.append(dict(stadium=st, source="central", rank=x.순위, title=x.중심관광지명,
                                  sigungu=x.중심시군구명))
    rk = pd.DataFrame(ranks)
    rk.to_csv(TAB / "d2_stadium_rank.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(courses).to_csv(PROC / "datalab_pre_course.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(stays).to_csv(PROC / "datalab_stay.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(stays).groupby("stadium").title.apply(lambda s: " | ".join(s)).to_string())
    print(rk.to_string(index=False))
    print(pd.DataFrame(courses).groupby("stadium").title.apply(lambda s: " | ".join(s)).to_string())


if __name__ == "__main__":
    main()
