"""
2단계 — 진단적 분석 (Diagnostic Analysis)
============================================
"왜 그런 패턴이 나오는가"를 교차분석으로 설명하는 단계.
계절성, 그리고 '풍속/시정/강수 중 무엇이 주된 제한 원인인가'를 분해합니다.
"""

import pandas as pd
import numpy as np
from .config import THRESHOLDS


def seasonal_availability_table(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    월별 가용률 테이블을 히트맵 입력 형태(수단 × 월)로 피벗.
    (descriptive.monthly_availability()의 출력을 받아 변환)
    """
    modes = list(THRESHOLDS.keys())
    pivot = monthly_df.set_index("month")[[f"availability_{m}" for m in modes]]
    pivot.columns = modes
    return pivot.T  # 행=수단, 열=월


def limiting_factor_breakdown(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    수단별 '운용 불가' 시간대 중, 어떤 기상요소가 원인이었는지 분해.
    (풍속초과 / 순간풍속초과 / 시정불량 / 강수과다 — 중복 계상 가능)

    이게 "원인 분해" 막대그래프의 원자료입니다.
    """
    rows = []
    for mode, th in THRESHOLDS.items():
        unavailable = hourly_df[hourly_df[f"op_{mode}"] == False]  # noqa: E712
        n_total_unavailable = len(unavailable)
        if n_total_unavailable == 0:
            rows.append({"mode": mode, "factor": "없음", "count": 0, "share": 0.0})
            continue

        factors = {
            "평균풍속 초과": (unavailable["wind_mps"] > th.max_wind_mps).sum(),
            "순간풍속 초과": (unavailable["gust_mps"] > th.max_gust_mps).sum(),
            "시정 불량": (unavailable["visibility_m"] < th.min_visibility_m).sum(),
            "강수 과다": (unavailable["precip_mm"] > th.max_precip_mm_h).sum(),
        }
        for factor, count in factors.items():
            rows.append({
                "mode": mode,
                "factor": factor,
                "count": int(count),
                "share": round(count / n_total_unavailable, 3),
            })
    return pd.DataFrame(rows)


def seasonal_isolation_concentration(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    '전수단 동시불가일'이 특정 계절에 얼마나 집중되는지 (계절성 진단).
    겨울철(12-2월) vs 그 외 비중을 비교해 "왜 겨울철 안전재고를 더 잡아야 하는가"의 근거로 사용.
    """
    df = daily_df.copy()
    df["month"] = df["date"].dt.month
    df["season"] = df["month"].map(
        lambda m: "겨울(12-2월)" if m in (12, 1, 2)
        else "환절기(3-4,11월)" if m in (3, 4, 11)
        else "그외(5-10월)"
    )
    total_by_season = df.groupby("season")["all_unavailable"].agg(["sum", "count"])
    total_by_season["rate"] = (total_by_season["sum"] / total_by_season["count"]).round(4)
    total_by_season.columns = ["동시불가일수", "전체일수", "동시불가비율"]
    return total_by_season.reindex(["겨울(12-2월)", "환절기(3-4,11월)", "그외(5-10월)"])


def station_topography_note() -> str:
    """
    공간정보(지형) 기반 위험 보정에 대한 주석.
    ⚠ 중요: 실제 풍속을 DEM으로 '예측'하지 않는다는 점을 명시.
    이 함수는 계산을 수행하지 않고, 제안서에 넣을 방어 문구를 반환하는 문서화 목적.
    """
    return (
        "본 분석은 관측·예보된 풍속·시정·강수 값을 그대로 사용합니다. "
        "수치표고모델(DEM)은 실제 풍속을 정량적으로 '예측'하는 데 사용하지 않으며, "
        "능선/계곡/해안 인접성 등 지형 노출 특성을 바탕으로 "
        "'풍속 증폭 취약 구간' 여부를 정성적 주의 플래그로만 표시하는 데 한정합니다."
    )
