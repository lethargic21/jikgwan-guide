"""데이터랩 수동 다운로드 zip 정리 → data/raw/datalab/{D1,D2,D3}/, 원본 zip은 _zip/.

- 파일 종류는 zip 안 파일명으로, 구장은 파일 **내용**으로 판별한다(zip 이름이 실제 내용과 다른 경우가 있었음).
  - D1(관광지출): '지역별 지출액'의 행정동 목록에 구장 소재 행정동이 있는지로 구장 판별
  - D2(중심·연관 관광지): '중심관광지 대시보드'의 시도·시군구명으로 구장 판별. 연관관광지 파일명에는 실제 중심관광지명을 붙인다
  - D3(국민여행조사): 그대로 보관
- 같은 내용의 파일(바이트 동일)은 표시해 둔다(예: 다른 시군구로 받았는데 연관관광지가 직전 것과 같은 경우)
- 결과 목록: data/raw/datalab/README.md
재실행 안전: _zip/에 있는 zip도 다시 읽어 같은 결과를 만든다.
"""
import csv
import hashlib
import io
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "data" / "raw" / "datalab"
ZIPDIR = DL / "_zip"

# 구장 ↔ (시도 키워드, 시군구명, 구장 소재 행정동)
STADIUMS = [
    ("잠실", "서울", "송파구", "잠실2동"),
    ("고척", "서울", "구로구", "고척1동"),
    ("문학", "인천", "미추홀구", "문학동"),
    ("수원", "경기", "수원시 장안구", "조원1동"),
    ("대전", "대전", "중구", "부사동"),
    ("대구", "대구", "수성구", "고산2동"),
    ("광주", "광주", "북구", "임동"),
    ("사직", "부산", "동래구", "사직2동"),
    ("창원", "경남", "창원시 마산회원구", "양덕2동"),
]


def member_name(info):
    n = info.filename
    if not info.flag_bits & 0x800:  # UTF-8 플래그가 없으면 cp949로 저장된 이름
        try:
            n = n.encode("cp437").decode("cp949")
        except UnicodeError:
            pass
    return Path(n).name


def rows(data):
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))


def d1_stadium(members):
    for name, data in members:
        if "지역별 지출액" in name:
            dongs = {r[0] for r in rows(data)[1:] if r}
            hits = [s for s in STADIUMS if s[3] in dongs]
            # 행정동 이름이 겹칠 수 있으니 관광소비 추이의 기초지자체명과 교차 확인
            sgg = {r[1] for n2, d2 in members if "관광소비 추이" in n2 for r in rows(d2)[1:2]}
            hits = [s for s in hits if s[2].split()[-1] in sgg] or hits
            if len(hits) == 1:
                return hits[0]
    return None


def d2_stadium(members):
    for name, data in members:
        if "중심관광지 대시보드" in name:
            r = rows(data)[1]
            sido, sgg = r[1], r[2]
            for s in STADIUMS:
                same_sgg = sgg in (s[2], s[2].split()[-1])
                same_sido = s[1] in sido or (s[0] == "광주" and "광주" in sido)  # 2026-07 '전남광주통합'
                if same_sgg and same_sido:
                    return s
    return None


def main():
    ZIPDIR.mkdir(parents=True, exist_ok=True)
    for z in DL.glob("*.zip"):
        shutil.move(str(z), ZIPDIR / z.name)
    log, seen = [], {}
    for sub in ["D1", "D2", "D3"]:
        (DL / sub).mkdir(exist_ok=True)
    for zp in sorted(ZIPDIR.glob("*.zip")):
        with zipfile.ZipFile(zp) as zf:
            members = [(member_name(i), zf.read(i)) for i in zf.infolist() if not i.is_dir()]
        names = " ".join(n for n, _ in members)
        if "관광소비 추이" in names:
            kind, st = "D1", d1_stadium(members)
        elif "중심관광지" in names or "연관관광지" in names:
            kind, st = "D2", d2_stadium(members)
        elif "국내여행" in names:
            kind, st = "D3", None
        else:
            kind, st = "기타", None
        for name, data in members:
            base = re.sub(r"^\d{14}_", "", name)  # 앞의 다운로드 시각 제거
            if kind == "D1":
                out = f"{st[0]}_{st[2].replace(' ', '')}_{base}"
            elif kind == "D2":
                m = re.search(r"\[(.+?)\]_연관관광지", base)
                out = (f"{st[0]}_{st[2].replace(' ', '')}_연관관광지_중심={m.group(1)}.csv" if m
                       else f"{st[0]}_{st[2].replace(' ', '')}_중심관광지.csv")
            elif kind == "D3":
                out = f"국민여행조사_2023-2025_{base}"
            else:
                out = base
            h = hashlib.md5(data).hexdigest()
            dup = seen.get(h)
            seen.setdefault(h, f"{kind}/{out}")
            (DL / kind).mkdir(exist_ok=True)
            (DL / kind / out).write_bytes(data)
            log.append((zp.name, kind, st[0] if st else "-", f"{kind}/{out}", dup or ""))
    lines = ["# 데이터랩 다운로드 정리 결과 (analysis/00_organize_datalab.py 자동 생성)", "",
             "| 원본 zip | 종류 | 구장(내용 기준) | 정리된 파일 | 같은 내용의 파일 |", "|---|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in log]
    (DL / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in log:
        print(" | ".join(row))


if __name__ == "__main__":
    main()
