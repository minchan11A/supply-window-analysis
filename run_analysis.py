"""
보급윈도우(Supply-Window) 분석 파이프라인 — 전체 실행 스크립트
===================================================================
사용법:
  실데이터: python run_analysis.py --csv data/raw/실제파일.csv --station "○○관측소"
  합성데이터(데모): python run_analysis.py --demo

3단계 분석을 순서대로 실행하고, 그래프 4종 + 요약 리포트를 outputs/에 저장합니다.
"""

import argparse
import json
from pathlib import Path

from src.load_data import load_kma_csv, generate_synthetic_data
from src.descriptive import (
    compute_hourly_operability, compute_daily_operability,
    mode_annual_availability, monthly_availability,
    longest_isolation_per_year, isolation_event_frequency, summary_report,
)
from src.diagnostic import (
    seasonal_availability_table, limiting_factor_breakdown,
    seasonal_isolation_concentration, station_topography_note,
)
from src.prescriptive import recommend_safety_stock_days, supply_window_recommendation, classify_current_status
from src.visualize import (
    plot_monthly_heatmap, plot_annual_isolation_trend,
    plot_isolation_calendar, plot_limiting_factor_breakdown,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, help="기상청 시간자료 CSV 경로")
    parser.add_argument("--station", type=str, default="", help="관측소/부대 이름 (그래프 제목용)")
    parser.add_argument("--demo", action="store_true", help="합성 데이터로 데모 실행")
    args = parser.parse_args()

    print("=" * 60)
    print(" 보급윈도우(Supply-Window) 분석 파이프라인")
    print("=" * 60)

    # ── 0. 데이터 로드 ──
    if args.demo or not args.csv:
        print("\n[0/3] 합성(가상) 데이터 생성 중... (⚠ 데모 전용, 실제 CSV로 교체 필요)")
        raw = generate_synthetic_data()
        station_name = args.station or "가상_도서관측소(데모)"
    else:
        print(f"\n[0/3] 실데이터 로드 중: {args.csv}")
        raw = load_kma_csv(args.csv)
        station_name = args.station or raw["station"].iloc[0]

    print(f"      기간: {raw['datetime'].min()} ~ {raw['datetime'].max()} "
          f"({len(raw):,} 시간 레코드)")

    # ── 1단계: 기술통계 ──
    print("\n[1/3] 1단계 — 기술통계(Descriptive) 계산 중...")
    hourly = compute_hourly_operability(raw)
    daily = compute_daily_operability(hourly)
    annual = mode_annual_availability(daily)
    monthly = monthly_availability(daily)
    per_year_iso = longest_isolation_per_year(daily)
    freq = isolation_event_frequency(daily)
    summary = summary_report(daily)

    print("      수단별 평균 연간 가용률:", summary["수단별_평균연간가용률"])
    print("      전체기간 최장 연속 고립일수:", summary["전체기간_최장연속고립일수"], "일")

    # ── 2단계: 진단적 분석 ──
    print("\n[2/3] 2단계 — 진단적 분석(Diagnostic) 계산 중...")
    seasonal_table = seasonal_availability_table(monthly)
    breakdown = limiting_factor_breakdown(hourly)
    seasonal_concentration = seasonal_isolation_concentration(daily)
    print("      계절별 동시불가 집중도:")
    print(seasonal_concentration.to_string())

    # ── 3단계: 처방적 로직 ──
    print("\n[3/3] 3단계 — 처방적 로직(Prescriptive) 계산 중...")
    safety = recommend_safety_stock_days(per_year_iso)
    print(f"      권고 안전재고: {safety['권고_안전재고_일수']}일분")
    print(f"      산정근거: {safety['산정근거']}")

    # 예시 시나리오: 오늘 상황에서의 보급 권고
    example = supply_window_recommendation(
        current_stock_days=3.2,
        recommended_safety_days=safety["권고_안전재고_일수"],
        mode_status_today={"선박": {"label": "가능", "operational_hours": 14},
                            "헬기": {"label": "가능", "operational_hours": 12},
                            "드론": {"label": "가능", "operational_hours": 16}},
        mode_status_24h={"선박": {"label": "제한적", "operational_hours": 3},
                          "헬기": {"label": "제한적", "operational_hours": 2},
                          "드론": {"label": "가능", "operational_hours": 10}},
        mode_status_48h={"선박": {"label": "불가", "operational_hours": 0},
                          "헬기": {"label": "불가", "operational_hours": 0},
                          "드론": {"label": "제한적", "operational_hours": 4}},
    )
    print(f"      예시 시나리오 판정: {example['판정']}")

    # ── 그래프 생성 ──
    print("\n[그래프] 4종 그래프 생성 중...")
    figs = []
    figs.append(plot_monthly_heatmap(seasonal_table, station_name))
    figs.append(plot_annual_isolation_trend(per_year_iso, safety["권고_안전재고_일수"]))
    demo_year = int(per_year_iso.loc[per_year_iso["max_isolation_days"].idxmax(), "year"])
    figs.append(plot_isolation_calendar(daily, demo_year))
    figs.append(plot_limiting_factor_breakdown(breakdown))
    for f in figs:
        print(f"      저장됨: {f}")

    # ── 결과 저장 ──
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)

    daily.to_csv(out_dir / "daily_operability.csv", index=False, encoding="utf-8-sig")
    annual.to_csv(out_dir / "annual_availability.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(out_dir / "monthly_availability.csv", index=False, encoding="utf-8-sig")
    breakdown.to_csv(out_dir / "limiting_factor_breakdown.csv", index=False, encoding="utf-8-sig")
    seasonal_concentration.to_csv(out_dir / "seasonal_concentration.csv", encoding="utf-8-sig")

    report = {
        "station": station_name,
        "summary_stage1": summary,
        "safety_stock_stage3": safety,
        "example_recommendation": example,
        "topography_disclaimer": station_topography_note(),
    }
    with open(out_dir / "analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n완료. CSV/JSON/그래프가 {out_dir.resolve()} 에 저장되었습니다.")
    print("=" * 60)


if __name__ == "__main__":
    main()
