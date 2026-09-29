"""공유 미리보기 이미지 web/og.png (1200×630) — 웹과 같은 다크 야구장 테마.
직접 그린 도형·글자만 쓴다(로고·사진 없음, §3-3). 수치는 분석 표에서 읽는다."""
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "outputs" / "tables"
pooled = pd.read_csv(TAB / "gameday_effect_pooled.csv")
pct = pooled[(pooled.spec == "pooled") & (pooled["var"] == "game")].pct.iloc[0]
eff = pd.read_csv(TAB / "gameday_effect_by_stadium.csv")
main9 = eff[(eff["var"] == "game") & (eff.secondary == 0)].set_index("stadium")
sh = pd.read_csv(TAB / "gameday_outsider_share_of_crowd.csv").set_index("stadium")
extra = round((sh.extra_outsiders_per_game_point * main9.n_game_days).sum() / main9.n_game_days.sum(), -2)
extra_txt = f"{int(extra // 10000)}만 {int(extra % 10000):,}명" if extra >= 10000 else f"{int(extra):,}명"

BG, CARD, BOARD = "#16120e", "#211a14", "#0d0a07"
INK, TEXT, MUTED = "#ffffff", "#efe8df", "#b3a796"
DIRT, AMBER, CHALK = "#e0925a", "#ffb000", "#f3e6d3"
W, H = 1200, 630

plt.rcParams["font.family"] = "Noto Sans KR"
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

# 조명탑 빛: 위쪽 양 모서리에서 퍼지는 따뜻한 백색
yy, xx = np.mgrid[0:H, 0:W]
glow = np.zeros((H, W))
for cx in (0, W):
    d = np.sqrt(((xx - cx) / 700) ** 2 + ((yy - H) / 520) ** 2)
    glow = np.maximum(glow, np.clip(1 - d, 0, 1) ** 2)
rgba = np.zeros((H, W, 4))
rgba[..., :3] = np.array([255, 226, 180]) / 255
rgba[..., 3] = glow * 0.22
ax.imshow(rgba, extent=(0, W, 0, H), origin="lower", zorder=0)

# 내야 다이아몬드 라인 (옅게)
cx, cy, r = 900, 250, 190
ax.add_patch(Polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], closed=True, fill=False,
                     edgecolor=CHALK, alpha=0.12, lw=2, zorder=1))
ax.plot([cx, cx + 2.2 * r], [cy - r, cy + 1.2 * r], color=CHALK, alpha=0.10, lw=2, zorder=1)
ax.plot([cx, cx - 2.2 * r], [cy - r, cy + 1.2 * r], color=CHALK, alpha=0.10, lw=2, zorder=1)

# 잔디 깎은 줄무늬 띠 + 분필 라인
for i, x0 in enumerate(range(0, W, 60)):
    ax.add_patch(Rectangle((x0, 0), 60, 34, color="#2b6532" if i % 2 == 0 else "#34763b", zorder=2))
ax.add_patch(Rectangle((0, 34), W, 3, color=CHALK, alpha=0.35, zorder=2))

# 왼쪽: 제목
ax.text(70, 548, "프로야구 홈경기일 관광 효과 측정 · 9개 구장 진단", fontsize=19, color=DIRT, fontweight="bold", va="center", zorder=3)
ax.text(70, 430, "경기날 몰려온 외지인,\n다음날엔 남지 않는다", fontsize=46, color=INK, fontweight="bold", va="center",
        linespacing=1.3, zorder=3)
ax.text(70, 300, "한국관광 데이터랩으로 측정한 9개 구장 진단과\n원정팬 체류 가이드", fontsize=20, color=TEXT, va="center",
        linespacing=1.5, zorder=3)
ax.text(70, 76, "한국관광 데이터랩 · TourAPI 활용 · 공모전용 개인 프로젝트", fontsize=14, color=MUTED, va="center", zorder=3)

# 오른쪽: 전광판
bx, by, bw, bh = 760, 150, 380, 250
ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0,rounding_size=14", facecolor=BOARD,
                            edgecolor=(1, 1, 1, 0.12), lw=1.5, zorder=3))
dots_x, dots_y = np.meshgrid(np.arange(bx + 10, bx + bw - 5, 9), np.arange(by + 10, by + bh - 5, 9))
ax.scatter(dots_x.ravel(), dots_y.ravel(), s=0.6, color=(1, 1, 1, 0.10), zorder=4, linewidths=0)
ax.text(bx + 28, by + bh - 36, "HOME GAME DAY", fontsize=13, color="#d9a441", fontfamily="DejaVu Sans Mono",
        fontweight="bold", va="center", zorder=5)
ax.text(bx + 24, by + bh / 2 + 8, f"+{pct:.1f}%", fontsize=64, color=AMBER, fontfamily="DejaVu Sans Mono",
        fontweight="bold", va="center", zorder=5)
ax.text(bx + 28, by + 40, f"경기당 외지인 약 {extra_txt}", fontsize=17, color=TEXT, va="center", zorder=5)

out = ROOT / "web" / "og.png"
fig.savefig(out, dpi=100, facecolor=BG)
print("saved", out, f"+{pct:.1f}%", extra_txt)
