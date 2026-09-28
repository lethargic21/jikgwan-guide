"""공유 미리보기 이미지 web/og.png (1200×630). 텍스트만 — 로고·사진 없음(§3-3). 수치는 분석 표에서 읽는다."""
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
pooled = pd.read_csv(ROOT / "outputs" / "tables" / "gameday_effect_pooled.csv")
pct = pooled[(pooled.spec == "pooled") & (pooled["var"] == "game")].pct.iloc[0]

BG, INK, INK2, ACC, STITCH = "#f7f6f3", "#0b0b0b", "#52514e", "#1d5fae", "#e34948"
plt.rcParams["font.family"] = "Noto Sans KR"
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1200)
ax.set_ylim(0, 630)
ax.axis("off")
# 공 실밥을 닮은 두 곡선 (장식, 로고 아님)
ax.add_patch(matplotlib.patches.Arc((1210, 315), 360, 520, theta1=100, theta2=260, color=STITCH, lw=4, alpha=.8))
ax.add_patch(matplotlib.patches.Arc((1330, 315), 360, 520, theta1=100, theta2=260, color=STITCH, lw=4, alpha=.35))
ax.text(80, 520, "가을야구 원정 직관 가이드", fontsize=26, color=ACC, fontweight="bold", va="center")
ax.text(80, 405, "경기만 보고 돌아오기엔\n아까운 하루", fontsize=54, color=INK, fontweight="bold", va="center", linespacing=1.25)
ax.text(80, 235, f"홈경기날 구장 동네 외지인 방문 +{pct:.1f}%", fontsize=30, color=INK, va="center")
ax.text(80, 180, "9개 구장 · 경기 전 코스 · 경기 후 한 끼 · 숙소 권역", fontsize=22, color=INK2, va="center")
ax.text(80, 70, "한국관광 데이터랩 · 한국관광공사 TourAPI 데이터를 활용한 개인 프로젝트", fontsize=16, color=INK2, va="center")
out = ROOT / "web" / "og.png"
fig.savefig(out, dpi=100, facecolor=BG)
print("saved", out)
