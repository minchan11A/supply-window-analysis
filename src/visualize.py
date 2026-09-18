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
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

# 한글 폰트 설정 (Noto Sans CJK KR — 컨테이너에 설치되어 있음)
KOREAN_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
try:
    fm.fontManager.addfont(KOREAN_FONT_PATH)
    # matplotlib only registers the first face of a .ttc collection;
    # for this Noto Sans CJK Regular file that face resolves to "Noto Sans CJK JP",
    # which still contains full Hangul coverage, so it renders Korean correctly.
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
except Exception:
    pass
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


def plot_marginal_contribution(marg: dict) -> Path:
    """8) 수단별 한계 보완 효과 — 타 수단이 모두 막혔을 때의 기여"""
    modes = ["선박", "헬기", "드론"]
    rescued = [marg[m]["해당수단_가용일"] for m in modes]
    remaining = [marg[m]["잔여고립일"] for m in modes]

    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    x = np.arange(len(modes))
    w = 0.55

    ax.bar(x, rescued, w, label="해당 수단이 보급창구를 연 날", color="#2c7fb8")
    ax.bar(x, remaining, w, bottom=rescued, label="그래도 고립된 날", color="#d0d5db")

    for i, m in enumerate(modes):
        total = rescued[i] + remaining[i]
        if rescued[i] > 0:
            ax.text(i, rescued[i]/2, f"{rescued[i]}일\n({marg[m]['기여율']}%)",
                    ha="center", va="center", color="white", fontsize=10, fontweight="bold")
        ax.text(i, total + 0.6, f"타 수단 전부 불가 {total}일",
                ha="center", fontsize=8.5, color="#555")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}" for m in modes])
    ax.set_ylabel("일수 (10년 누적)")
    ax.set_title("수단별 한계 보완 효과 — 다른 수단이 모두 막혔을 때")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_ylim(0, max(r+rm for r, rm in zip(rescued, remaining)) + 5)
    fig.tight_layout()
    out = FIG_DIR / "08_marginal_contribution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
