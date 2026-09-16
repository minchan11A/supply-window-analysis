"""
보급윈도우(Supply-Window) 분석 설정
====================================
각 수단(선박/헬기/드론)의 운용 한계기준을 여기서 관리합니다.
출처: 교범·장비 제원·국방표준(가상 값 — 실제 값으로 교체 필요)

주의: 이 기준은 예시값입니다. 실제 제안서에는
      해당 기종의 실제 운용교범·제원표에서 발췌한 수치를 넣어야 합니다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModeThreshold:
    """수단별 운용 가능 한계기준"""
    name: str
    max_wind_mps: float          # 한계 평균풍속 (m/s)
    max_gust_mps: float          # 한계 순간최대풍속 (m/s)
    min_visibility_m: float      # 최소 시정 (m)
    max_precip_mm_h: float       # 최대 시간강수량 (mm/h)
    max_wave_height_m: float = None  # 최대 파고 (선박만 해당, m)
    source: str = ""             # 근거 출처(교범/제원 조항 — 실제 값으로 교체)


# ── 수단별 임계값 테이블 (예시값, 반드시 실제 교범값으로 교체) ──
THRESHOLDS = {
    "선박": ModeThreshold(
        name="선박",
        max_wind_mps=14.0,
        max_gust_mps=18.0,
        min_visibility_m=1000,
        max_precip_mm_h=15.0,
        max_wave_height_m=2.5,
        source="예시값 — 함정 운용교범 발췌 필요",
    ),
    "헬기": ModeThreshold(
        name="헬기",
        max_wind_mps=15.0,
        max_gust_mps=20.0,
        min_visibility_m=1600,
        max_precip_mm_h=10.0,
        source="예시값 — 항공운용교범 발췌 필요",
    ),
    "드론": ModeThreshold(
        name="드론",
        max_wind_mps=8.0,
        max_gust_mps=12.0,
        min_visibility_m=500,
        max_precip_mm_h=3.0,
        source="예시값 — 국방기술품질원 25kg급 국방표준 발췌 필요",
    ),
}

# 하루 중 "운용 가능"으로 인정하기 위한 최소 연속 가능 시간(시간 단위)
# 예: 6시간 이상 조건을 만족해야 그날을 '운용가능일'로 카운트
MIN_OPERATIONAL_WINDOW_HOURS = 6

# 안전재고 산정에 쓸 백분위수 (꼬리분포 대응 — 평균이 아닌 극단값 기준)
SAFETY_STOCK_PERCENTILE = 95

# 고립(3개 수단 모두 불가) 판정 시, "연속 고립 사건"으로 집계할 최소 일수
MIN_ISOLATION_EVENT_DAYS = 3
