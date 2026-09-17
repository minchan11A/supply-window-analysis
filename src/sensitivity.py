"""
민감도 분석 (Sensitivity Analysis)
=====================================
운용 임계값(풍속·시정·강수)을 ±범위로 흔들어도
핵심 결론이 유지되는지(robustness) 검증합니다.

심사 방어 목적:
  "임계값 근거가 약한 것 아닌가?"라는 질문에 대해
  "임계값을 보수적/완화 방향 양쪽으로 흔들어도
   '시정이 지배적 제약'이라는 결론은 바뀌지 않는다"고 답하기 위함.
"""

import pandas as pd
import numpy as np
from copy import deepcopy

from .config import THRESHOLDS, ModeThreshold, MIN_OPERATIONAL_WINDOW_HOURS
from .descriptive import compute_daily_operability, longest_isolation_per_year
from .prescriptive import recommend_safety_stock_days


def _apply_scenario(raw_df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """주어진 임계값 세트로 시간별 운용가능 여부를 계산 (벡터화 연산)"""
    out = raw_df.copy()
    for mode, th in thresholds.items():
        ok = pd.Series(True, index=out.index)
        ok &= out["wind_mps"].le(th.max_wind_mps) | out["wind_mps"].isna()
        ok &= out["gust_mps"].le(th.max_gust_mps) | out["gust_mps"].isna()
        ok &= out["visibility_m"].ge(th.min_visibility_m) | out["visibility_m"].isna()
        ok &= out["precip_mm"].le(th.max_precip_mm_h) | out["precip_mm"].isna()
        out[f"op_{mode}"] = ok
    return out


def _scale_thresholds(base: dict, wind_factor: float = 1.0,
                       vis_factor: float = 1.0, precip_factor: float = 1.0) -> dict:
    """
    임계값을 배수로 조정한 새 세트를 생성.

    wind_factor < 1  → 풍속 기준을 더 엄격하게 (보수적)
    vis_factor  > 1  → 요구 시정을 더 높게 (보수적)
    """
    scaled = {}
    for mode, th in base.items():
        scaled[mode] = ModeThreshold(
            name=th.name,
            max_wind_mps=th.max_wind_mps * wind_factor,
            max_gust_mps=th.max_gust_mps * wind_factor,
            min_visibility_m=th.min_visibility_m * vis_factor,
            max_precip_mm_h=th.max_precip_mm_h * precip_factor,
            max_wave_height_m=th.max_wave_height_m,
            source=f"{th.source} (민감도 시나리오)",
        )
    return scaled


def run_sensitivity(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    5개 시나리오(기준 / 보수적 / 완화 / 시정만 강화 / 풍속만 강화)에 대해
    가용률·고립일수·권고 안전재고를 비교.
    """
    scenarios = {
        "기준 (Baseline)":        dict(wind_factor=1.0,  vis_factor=1.0, precip_factor=1.0),
        "보수적 (-20% 엄격)":     dict(wind_factor=0.8,  vis_factor=1.5, precip_factor=0.7),
        "완화 (+20% 관대)":       dict(wind_factor=1.2,  vis_factor=0.7, precip_factor=1.3),
        "시정만 강화 (×2)":       dict(wind_factor=1.0,  vis_factor=2.0, precip_factor=1.0),
        "풍속만 강화 (-30%)":     dict(wind_factor=0.7,  vis_factor=1.0, precip_factor=1.0),
    }

    rows = []
    for name, params in scenarios.items():
        th = _scale_thresholds(THRESHOLDS, **params)
        hourly = _apply_scenario(raw_df, th)
        daily = compute_daily_operability(hourly)
        per_year = longest_isolation_per_year(daily)
        safety = recommend_safety_stock_days(per_year)

        row = {"시나리오": name}
        for mode in THRESHOLDS:
            row[f"가용률_{mode}"] = round(daily[f"opday_{mode}"].mean() * 100, 1)
        row["동시불가일수"] = int(daily["all_unavailable"].sum())
        row["최장고립일"] = int(per_year["max_isolation_days"].max())
        row["권고안전재고"] = safety["권고_안전재고_일수"]

        # 원인 분해: 시정이 지배적인지 확인 (선박 기준)
        unav = hourly[hourly["op_선박"] == False]  # noqa: E712
        if len(unav) > 0:
            th_ship = th["선박"]
            row["선박_시정기인%"] = round(
                (unav["visibility_m"] < th_ship.min_visibility_m).sum() / len(unav) * 100, 1
            )
            row["선박_풍속기인%"] = round(
                (unav["wind_mps"] > th_ship.max_wind_mps).sum() / len(unav) * 100, 1
            )
        else:
            row["선박_시정기인%"] = np.nan
            row["선박_풍속기인%"] = np.nan
        rows.append(row)

    return pd.DataFrame(rows)


def run_threshold_sweep(raw_df: pd.DataFrame, mode: str = "선박") -> pd.DataFrame:
    """
    특정 수단의 시정 임계값을 연속적으로 변화시키며 가용률 변화를 추적.
    → "임계값이 몇 m일 때 가용률이 급변하는가"를 보여주는 곡선.
    """
    base = THRESHOLDS[mode]
    vis_values = [200, 400, 600, 800, 1000, 1500, 2000, 3000, 5000]
    rows = []
    for v in vis_values:
        th = deepcopy(THRESHOLDS)
        th[mode] = ModeThreshold(
            name=base.name, max_wind_mps=base.max_wind_mps,
            max_gust_mps=base.max_gust_mps, min_visibility_m=v,
            max_precip_mm_h=base.max_precip_mm_h,
            max_wave_height_m=base.max_wave_height_m, source=base.source,
        )
        hourly = _apply_scenario(raw_df, th)
        daily = compute_daily_operability(hourly)
        rows.append({
            "요구시정_m": v,
            "가용률_%": round(daily[f"opday_{mode}"].mean() * 100, 2),
        })
    return pd.DataFrame(rows)
