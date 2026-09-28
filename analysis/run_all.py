"""전체 분석을 순서대로 실행한다.

  .venv/Scripts/python analysis/run_all.py

01(방문자 API)·06(TourAPI)은 data/raw/api/ 캐시가 있으면 호출하지 않는다.
"""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ["00_fetch_kbo.py", "00_organize_datalab.py", "01_collect_visitors.py", "02_build_panel.py",
           "03_gameday_effect.py", "05_sido_auxiliary.py",
           "09_spending_describe.py", "10_datalab_d2.py",  # 데이터랩 D1·D2 (04·07보다 먼저)
           "11_expected_effect.py",  # D3(국민여행조사 PDF) + 05의 유입 비율
           "04_figures.py",  # 03·05·09의 표를 쓴다
           "06_tourapi_places.py", "07_build_web_data.py", "08_og_image.py"]
for script in SCRIPTS:
    print(f"\n===== {script} =====")
    runpy.run_path(str(HERE / script), run_name="__main__")
