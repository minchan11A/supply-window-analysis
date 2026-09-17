"""
시각화 모듈
=============
제안서에 실제로 넣을 4종 그래프를 생성합니다.
  1) 월별×수단별 가용률 히트맵
  2) 연도별 최장 고립일수 추이
  3) 동시불가 캘린더 히트그리드 (GitHub contribution 그래프 형태)
  4) 수단별 한계초과 원인 분해 막대그래프
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
import numpy as np
import warnings
from pathlib import Path

# ── 한글 폰트 설정 ──────────────────────────────────────────
# 환경마다 설치된 한글 폰트가 다르므로 고정 경로에 의존하지 않는다.
# 후보를 순서대로 시도하고, 하나도 없으면 조용히 넘어가지 말고 경고한다.
# (조용히 실패하면 그래프의 한글이 모두 □ 로 깨진 채 생성된다.)
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",            # macOS
    "C:/Windows/Fonts/malgun.ttf",               # Windows
]


def _setup_korean_font() -> str | None:
    """사용 가능한 한글 폰트를 찾아 matplotlib 기본 폰트로 등록한다."""
    # 1) 알려진 경로 탐색
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                fm.fontManager.addfont(path)
                name = fm.FontProperties(fname=path).get_name()
                # 한글 폰트 우선, 없는 글리프(U+2212 등)는 DejaVu Sans로 폴백.
                # NanumGothic 등 일부 한글 폰트는 유니코드 마이너스가 없어
                # 로그축 지수(10⁻¹)가 □로 깨진다.
                plt.rcParams["font.family"] = [name, "DejaVu Sans"]
                return name
            except Exception:
                continue

    # 2) 경로에 없으면 등록된 폰트 중 한글 이름을 가진 것을 탐색
    for keyword in ("Noto Sans CJK", "NanumGothic", "NanumBarunGothic",
                    "Malgun Gothic", "AppleGothic", "WenQuanYi"):
        for f in fm.fontManager.ttflist:
            if keyword.lower() in f.name.lower():
                plt.rcParams["font.family"] = [f.name, "DejaVu Sans"]
                return f.name

    warnings.warn(
        "한글 폰트를 찾지 못했습니다. 그래프의 한글이 깨져(□) 출력됩니다.\n"
        "  Ubuntu/Debian: sudo apt-get install -y fonts-nanum && fc-cache -f\n"
        "  macOS/Windows: 시스템 기본 한글 폰트가 자동 탐지됩니다.",
        RuntimeWarning, stacklevel=2,
    )
    return None


KOREAN_FONT = _setup_korean_font()
plt.rcParams["axes.unicode_minus"] = False

FIG_DIR = Path(__file__).resolve().parent.parent / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def plot_monthly_heatmap(seasonal_table: pd.DataFrame, station_name: str = "") -> Path:
    """1) 월별×수단별 가용률 히트맵"""
    fig, ax = plt.subplots(figsize=(11, 3.5))
    sns.heatmap(
        seasonal_table * 100,
        annot=True, fmt=".0f", cmap="RdYlGn", vmin=0, vmax=100,
        cbar_kws={"label": "가용률 (%)"}, ax=ax,
        linewidths=0.5, linecolor="white",
    )
    ax.set_xlabel("월")
    ax.set_ylabel("보급수단")
    ax.set_title(f"월별 × 수단별 운용 가용률{('  — ' + station_name) if station_name else ''}")
    fig.tight_layout()
    out = FIG_DIR / "01_monthly_availability_heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_annual_isolation_trend(per_year_isolation: pd.DataFrame,
                                  safety_stock_days: int = None) -> Path:
    """2) 연도별 최장 고립일수 추이"""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(per_year_isolation["year"], per_year_isolation["max_isolation_days"],
           color="#3b6ea5")
    ax.plot(per_year_isolation["year"], per_year_isolation["max_isolation_days"],
            color="#1a3a5c", marker="o")

    if safety_stock_days is not None:
        ax.axhline(safety_stock_days, color="crimson", linestyle="--", linewidth=1.5,
                    label=f"권고 안전재고 {safety_stock_days}일")
        ax.legend()

    ax.set_xlabel("연도")
    ax.set_ylabel("최장 연속 고립일수 (일)")
    ax.set_title("연도별 최장 연속 고립일수 추이 (전수단 동시 운용불가)")
    ax.set_xticks(per_year_isolation["year"])
    fig.tight_layout()
    out = FIG_DIR / "02_annual_isolation_trend.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_isolation_calendar(daily_df: pd.DataFrame, year: int) -> Path:
    """3) 동시불가 캘린더 히트그리드 (특정 연도, GitHub 잔디 스타일)"""
    df = daily_df[daily_df["date"].dt.year == year].copy()
    df = df.set_index("date").reindex(
        pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    )
    df["all_unavailable"] = df["all_unavailable"].fillna(0)

    df["weekday"] = df.index.weekday
    df["week"] = ((df.index - pd.Timestamp(f"{year}-01-01")).days + 
                   pd.Timestamp(f"{year}-01-01").weekday()) // 7

    grid = df.pivot_table(index="weekday", columns="week", values="all_unavailable", fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 2.2))
    sns.heatmap(grid, cmap=["#ebedf0", "#c0392b"], cbar=False, linewidths=1,
                linecolor="white", ax=ax, square=True)
    ax.set_title(f"{year}년 전수단 동시 운용불가일 캘린더 (빨강 = 3개 수단 모두 불가)")
    ax.set_xlabel("주차")
    ax.set_ylabel("요일")
    ax.set_yticklabels(["월", "화", "수", "목", "금", "토", "일"], rotation=0)
    ax.set_xticks([])
    fig.tight_layout()
    out = FIG_DIR / f"03_isolation_calendar_{year}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_limiting_factor_breakdown(breakdown_df: pd.DataFrame) -> Path:
    """
    4) 수단별 한계초과 원인 분해 막대그래프.

    ⚠ 그룹형(묶음) 막대를 사용합니다. 하나의 '운용불가 시간'이 풍속초과와
    시정불량을 동시에 유발할 수 있어(중복 계상 가능) 원인별 비중의 합이
    100%를 넘을 수 있으므로, 누적(stacked) 막대는 오해를 줄 수 있습니다.
    """
    pivot = breakdown_df.pivot(index="mode", columns="factor", values="share").fillna(0)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot.plot(kind="bar", stacked=False, ax=ax,
               color=sns.color_palette("Set2", n_colors=len(pivot.columns)))
    ax.set_ylabel("불가 시간대 중 해당 요인이 원인이었던 비중")
    ax.set_xlabel("보급수단")
    ax.set_title("수단별 운용불가 원인 분해 (풍속/시정/강수 — 중복 계상 가능)")
    ax.set_ylim(0, 1.05)
    ax.legend(title="제한 요인", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_xticklabels(pivot.index, rotation=0)
    fig.tight_layout()
    out = FIG_DIR / "04_limiting_factor_breakdown.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_sensitivity(sens_df: pd.DataFrame) -> Path:
    """5) 민감도 분석 — 시나리오별 원인 기여도 (결론 강건성 입증)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.2))

    x = np.arange(len(sens_df))
    w = 0.38
    ax1.bar(x - w/2, sens_df["선박_시정기인%"], w, label="시정 불량", color="#2c7fb8")
    ax1.bar(x + w/2, sens_df["선박_풍속기인%"], w, label="풍속 초과", color="#e07b39")
    ax1.set_xticks(x)
    ax1.set_xticklabels(sens_df["시나리오"], rotation=20, ha="right", fontsize=8)
    ax1.set_ylabel("선박 운용불가 원인 기여도 (%)")
    ax1.set_title("임계값을 바꿔도 시정이 지배적 제약")
    ax1.legend()
    ax1.set_ylim(0, 105)

    ax2.bar(x, sens_df["권고안전재고"], color="#3b6ea5")
    ax2.set_xticks(x)
    ax2.set_xticklabels(sens_df["시나리오"], rotation=20, ha="right", fontsize=8)
    ax2.set_ylabel("권고 안전재고 (일분)")
    ax2.set_title("권고 안전재고의 강건성")
    ax2.set_ylim(0, max(sens_df["권고안전재고"]) + 2)
    for i, v in enumerate(sens_df["권고안전재고"]):
        ax2.text(i, v + 0.1, str(v), ha="center", fontsize=10)

    fig.tight_layout()
    out = FIG_DIR / "05_sensitivity_analysis.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_return_level(return_analysis: dict, recommended: int = 3) -> Path:
    """6) 재현기간별 고립일수 (복합 포아송-기하 모형)"""
    curve = return_analysis["초과확률곡선"]
    days = [c["고립일수"] for c in curve]
    probs = [c["초과확률"] for c in curve]

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.semilogy(days, probs, marker="o", color="#0b3d91", linewidth=2, markersize=7)

    for T, style in [(5, ":"), (20, "--"), (50, "-.")]:
        ax.axhline(1/T, color="#999", linestyle=style, linewidth=1)
        ax.text(days[-1], 1/T, f" {T}년", va="center", fontsize=8, color="#666")

    ax.axvline(recommended, color="crimson", linestyle="--", linewidth=1.6)
    ax.text(recommended, probs[0], f" 권고 {recommended}일분", color="crimson",
            fontsize=9, va="top", ha="left")

    ax.set_xlabel("연속 고립일수 (일)")
    ax.set_ylabel("연최대 초과확률 (로그척도)")
    ax.set_title("재현기간별 고립 수준 — 복합 포아송-기하 모형")
    ax.set_xticks(days)

    # 로그축 기본 눈금은 mathtext(10^{-1})로 그려지는데, 일부 한글 폰트에는
    # 유니코드 마이너스(U+2212)가 없어 지수가 □로 깨진다.
    # mathtext를 쓰지 않는 일반 소수 표기로 고정해 환경에 관계없이 안전하게 만든다.
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda y, _: ("0" if y == 0 else
                      f"{y:.10f}".rstrip("0").rstrip(".") if y < 1 else f"{y:g}")))
    ax.yaxis.set_minor_formatter(ticker.NullFormatter())

    ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    out = FIG_DIR / "06_return_level.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_terrain_sensitivity(terr_df: pd.DataFrame) -> Path:
    """7) 지형 대표성 민감도 — 부대 풍속이 관측소보다 높다면?"""
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    x = np.arange(len(terr_df))

    ax.plot(x, terr_df["가용률_드론"], marker="o", color="#e07b39",
            linewidth=2.2, label="드론", markersize=7)
    ax.plot(x, terr_df["가용률_선박"], marker="s", color="#2c7fb8",
            linewidth=2.2, label="선박", markersize=6)
    ax.plot(x, terr_df["가용률_헬기"], marker="^", color="#5aa469",
            linewidth=2.2, label="헬기", markersize=6)

    ax.set_xticks(x)
    ax.set_xticklabels(terr_df["풍속_가정"], fontsize=9)
    ax.set_ylabel("연간 가용률 (%)")
    ax.set_title("지형 대표성 민감도 — 부대 실제 풍속이 관측소보다 높을 경우")
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(alpha=0.25, axis="y")

    for i, v in enumerate(terr_df["가용률_드론"]):
        ax.annotate(f"{v}", (i, v), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=8, color="#c2610f")

    fig.tight_layout()
    out = FIG_DIR / "07_terrain_sensitivity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
