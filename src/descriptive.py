"""
1단계 — 기술통계 (Descriptive Analysis)
=========================================
"무슨 일이 있었는가"를 숫자로 확정하는 단계.
여기서 나오는 모든 지표는 재현 가능한 단순 집계/카운트이며,
예측 모델이 전혀 필요하지 않습니다. (Cold-Start 방어의 핵심)
"""

import pandas as pd
import numpy as np
from .config import THRESHOLDS, MIN_OPERATIONAL_WINDOW_HOURS, MIN_ISOLATION_EVENT_DAYS


def is_hour_operational(row: pd.Series, mode: str) -> bool:
    """특정 시간대(1행)가 해당 수단 운용기준을 만족하는지 판정 (룰 기반)"""
    th = THRESHOLDS[mode]
    ok = True
    if not pd.isna(row["wind_mps"]):
        ok &= row["wind_mps"] <= th.max_wind_mps
    if not pd.isna(row.get("gust_mps")):
        ok &= row["gust_mps"] <= th.max_gust_mps
    if not pd.isna(row.get("visibility_m")):
        ok &= row["visibility_m"] >= th.min_visibility_m
    if not pd.isna(row.get("precip_mm")):
        ok &= row["precip_mm"] <= th.max_precip_mm_h
    return bool(ok)


def compute_hourly_operability(df: pd.DataFrame) -> pd.DataFrame:
    """시간자료에 수단별 운용가능 여부(0/1) 컬럼을 추가"""
    out = df.copy()
    for mode in THRESHOLDS:
        out[f"op_{mode}"] = out.apply(lambda r: is_hour_operational(r, mode), axis=1)
    return out


def compute_daily_operability(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    시간자료 → 일자료로 집계.
    '운용가능일' 정의: 해당 수단의 운용가능 시간대 합이
                      MIN_OPERATIONAL_WINDOW_HOURS 이상인 날 = 1
    """
    df = hourly_df.copy()
    df["date"] = df["datetime"].dt.date

    records = []
    for date, g in df.groupby("date"):
        row = {"date": date}
        for mode in THRESHOLDS:
            hours_ok = g[f"op_{mode}"].sum()
            row[f"opday_{mode}"] = int(hours_ok >= MIN_OPERATIONAL_WINDOW_HOURS)
            row[f"hours_ok_{mode}"] = int(hours_ok)
        records.append(row)

    daily = pd.DataFrame(records)
    daily["date"] = pd.to_datetime(daily["date"])
    daily["all_unavailable"] = (
        (daily[[f"opday_{m}" for m in THRESHOLDS]].sum(axis=1) == 0)
    ).astype(int)
    return daily.sort_values("date").reset_index(drop=True)


def mode_annual_availability(daily_df: pd.DataFrame) -> pd.DataFrame:
    """수단별 연간 가용률 = Σ운용가능일 / 365(또는 366)"""
    daily_df = daily_df.copy()
    daily_df["year"] = daily_df["date"].dt.year
    rows = []
    for year, g in daily_df.groupby("year"):
        n_days = len(g)
        row = {"year": year, "n_days": n_days}
        for mode in THRESHOLDS:
            row[f"availability_{mode}"] = g[f"opday_{mode}"].sum() / n_days
        rows.append(row)
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def monthly_availability(daily_df: pd.DataFrame) -> pd.DataFrame:
    """월별 × 수단별 가용률 (계절성 확인용 — 히트맵 원자료)"""
    daily_df = daily_df.copy()
    daily_df["month"] = daily_df["date"].dt.month
    rows = []
    for month, g in daily_df.groupby("month"):
        row = {"month": month}
        for mode in THRESHOLDS:
            row[f"availability_{mode}"] = g[f"opday_{mode}"].mean()
        rows.append(row)
    return pd.DataFrame(rows).sort_values("month").reset_index(drop=True)


def longest_isolation_runs(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    '전수단 동시 불가일(all_unavailable=1)'의 연속 구간(run-length)을 계산.
    → 연도별 최장 연속 고립일수, 고립 사건(≥ MIN_ISOLATION_EVENT_DAYS) 목록 산출
    """
    df = daily_df.sort_values("date").reset_index(drop=True).copy()
    df["group"] = (df["all_unavailable"] != df["all_unavailable"].shift()).cumsum()

    runs = (
        df[df["all_unavailable"] == 1]
        .groupby("group")
        .agg(start=("date", "min"), end=("date", "max"), length=("date", "count"))
        .reset_index(drop=True)
        .sort_values("start")
    )
    return runs


def longest_isolation_per_year(daily_df: pd.DataFrame) -> pd.DataFrame:
    """연도별 최장 연속 고립일수 (트렌드 그래프용)"""
    runs = longest_isolation_runs(daily_df)
    if runs.empty:
        years = sorted(daily_df["date"].dt.year.unique())
        return pd.DataFrame({"year": years, "max_isolation_days": [0] * len(years)})

    runs = runs.copy()
    runs["year"] = pd.to_datetime(runs["start"]).dt.year
    per_year = runs.groupby("year")["length"].max().reset_index()
    per_year.columns = ["year", "max_isolation_days"]

    # 고립이 아예 없었던 연도도 0으로 채움
    all_years = pd.DataFrame({"year": sorted(daily_df["date"].dt.year.unique())})
    per_year = all_years.merge(per_year, on="year", how="left").fillna(0)
    per_year["max_isolation_days"] = per_year["max_isolation_days"].astype(int)
    return per_year


def isolation_event_frequency(daily_df: pd.DataFrame) -> pd.DataFrame:
    """연도별 '장기 고립 사건'(길이 ≥ MIN_ISOLATION_EVENT_DAYS) 발생 횟수 (빈도분석)"""
    runs = longest_isolation_runs(daily_df)
    all_years = pd.DataFrame({"year": sorted(daily_df["date"].dt.year.unique())})

    if runs.empty:
        all_years["event_count"] = 0
        return all_years

    runs = runs.copy()
    runs["year"] = pd.to_datetime(runs["start"]).dt.year
    long_events = runs[runs["length"] >= MIN_ISOLATION_EVENT_DAYS]
    counts = long_events.groupby("year").size().reset_index(name="event_count")

    out = all_years.merge(counts, on="year", how="left").fillna(0)
    out["event_count"] = out["event_count"].astype(int)
    return out


def summary_report(daily_df: pd.DataFrame) -> dict:
    """1단계 기술통계 핵심 수치 요약 (제안서 본문에 바로 인용 가능한 형태)"""
    annual = mode_annual_availability(daily_df)
    per_year_iso = longest_isolation_per_year(daily_df)
    freq = isolation_event_frequency(daily_df)

    return {
        "분석기간_연도수": daily_df["date"].dt.year.nunique(),
        "총관측일수": len(daily_df),
        "수단별_평균연간가용률": {
            mode: round(annual[f"availability_{mode}"].mean(), 3) for mode in THRESHOLDS
        },
        "전체기간_최장연속고립일수": int(per_year_iso["max_isolation_days"].max()),
        "연도별_장기고립사건_평균발생횟수": round(freq["event_count"].mean(), 2),
        "전수단_동시불가_총일수": int(daily_df["all_unavailable"].sum()),
    }
