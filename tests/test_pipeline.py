"""
기본 동작 검증 테스트 (pytest)
================================
실행: pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.load_data import generate_synthetic_data
from src.descriptive import (
    compute_hourly_operability, compute_daily_operability,
    mode_annual_availability, longest_isolation_per_year,
    longest_isolation_runs, summary_report,
)
from src.diagnostic import limiting_factor_breakdown, seasonal_isolation_concentration
from src.prescriptive import recommend_safety_stock_days, classify_current_status


def _small_daily_df():
    raw = generate_synthetic_data(start="2020-01-01", end="2021-12-31", seed=1)
    hourly = compute_hourly_operability(raw)
    return compute_daily_operability(hourly), hourly


def test_synthetic_data_shape():
    df = generate_synthetic_data(start="2020-01-01", end="2020-01-31")
    # pd.date_range(freq="h")는 start~end를 '시각' 기준 양끝 포함으로 생성하므로
    # 2020-01-01 00:00 ~ 2020-01-31 00:00 은 30일 간격 + 1시간(양끝 포함)
    expected = int((pd.Timestamp("2020-01-31") - pd.Timestamp("2020-01-01")) / pd.Timedelta(hours=1)) + 1
    assert len(df) == expected
    assert {"datetime", "wind_mps", "gust_mps", "visibility_m", "precip_mm"}.issubset(df.columns)


def test_daily_operability_binary():
    daily, _ = _small_daily_df()
    for col in ["opday_선박", "opday_헬기", "opday_드론", "all_unavailable"]:
        assert set(daily[col].unique()).issubset({0, 1})


def test_annual_availability_range():
    daily, _ = _small_daily_df()
    annual = mode_annual_availability(daily)
    for mode in ["선박", "헬기", "드론"]:
        assert (annual[f"availability_{mode}"] >= 0).all()
        assert (annual[f"availability_{mode}"] <= 1).all()


def test_isolation_runs_consistency():
    """연속 고립일수 run-length 합이 전체 all_unavailable 합과 일치해야 함"""
    daily, _ = _small_daily_df()
    runs = longest_isolation_runs(daily)
    assert runs["length"].sum() == daily["all_unavailable"].sum()


def test_safety_stock_is_int_and_positive():
    daily, _ = _small_daily_df()
    per_year = longest_isolation_per_year(daily)
    result = recommend_safety_stock_days(per_year)
    assert isinstance(result["권고_안전재고_일수"], int)
    assert result["권고_안전재고_일수"] >= 1


def test_limiting_factor_breakdown_shares_bounded():
    daily, hourly = _small_daily_df()
    breakdown = limiting_factor_breakdown(hourly)
    assert (breakdown["share"] >= 0).all()
    assert (breakdown["share"] <= 1.0001).all()  # 부동소수 오차 허용


def test_classify_current_status_no_probability_leak():
    """상태 라벨에 확률(%) 표현이 섞이지 않는지 확인 (설계 원칙 방어)"""
    status = classify_current_status({"드론": 10, "헬기": 3, "선박": 0}, min_window_hours=6)
    for mode, s in status.items():
        assert s["label"] in {"가능", "제한적", "불가"}


def test_summary_report_keys():
    daily, _ = _small_daily_df()
    summary = summary_report(daily)
    expected_keys = {
        "분석기간_연도수", "총관측일수", "수단별_평균연간가용률",
        "전체기간_최장연속고립일수", "연도별_장기고립사건_평균발생횟수",
        "전수단_동시불가_총일수",
    }
    assert expected_keys.issubset(summary.keys())


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
