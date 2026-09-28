"""KBO 경기·관중 원자료 내려받기 (저장소에 재배포하지 않으므로 재현할 때 이 스크립트로 받는다).

출처: 공개 GitHub 저장소 KENNYSOFT/kbo-crowd (KBO 기록실 원자료 정리본, 라이선스 표기 없음)
검증: 2023~2025 시즌 총관중이 공식 발표와 일치 (data/raw/kbo/SOURCE.md)
"""
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "kbo"
BASE = "https://raw.githubusercontent.com/KENNYSOFT/kbo-crowd/main/data/"

OUT.mkdir(parents=True, exist_ok=True)
for name in ["games.csv", "schedule.csv", "stadiums.csv", "holidays.csv"]:
    path = OUT / name
    if path.exists():
        continue
    r = requests.get(BASE + name, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    print("saved", path)
    time.sleep(1.1)
