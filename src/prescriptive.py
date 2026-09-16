"""
3단계 — 처방적 로직 (Prescriptive, 예측 모델 아님)
======================================================
1·2단계의 통계 결과를 "안전재고 기준"이라는 의사결정 규칙으로 변환.

⚠ 중요한 방어 포인트:
   이 모듈은 예측 모델(머신러닝)이 아니라 "백분위수 기반 통계적 임계값 설정"입니다.
   평균이 아니라 꼬리분포(상위 백분위)를 쓰는 이유는
   "최악의 해에도 버티려면 평균이 아니라 꼬리분포를 봐야 한다"는 점을 명시합니다.
"""

import pandas as pd
import numpy as np
from .config import SAFETY_STOCK_PERCENTILE


def recommend_safety_stock_days(per_year_isolation: pd.DataFrame,
                                  percentile: int = SAFETY_STOCK_PERCENTILE) -> dict:
    """
    연도별 '최장 연속 고립일수' 분포에서 백분위수를 계산해 안전재고 기준(일수)을 산출.

    예: 10개 연도 값 중 95백분위 = 최악에 가까운 해의 고립일수
        → 이 값을 안전재고 기준일수로 권고 (올림 처리, 최소 여유 +1일)
    """
    values = per_year_isolation["max_isolation_days"].values
    p = np.percentile(values, percentile)
    recommended = int(np.ceil(p)) + 1  # 안전 마진 1일 추가

    return {
        "표본_연도수": len(values),
        "연도별_최장고립일수_목록": values.tolist(),
        "평균_최장고립일수": round(float(np.mean(values)), 2),
        f"{percentile}백분위_최장고립일수": round(float(p), 2),
        "권고_안전재고_일수": recommended,
        "산정근거": (
            f"최근 {len(values)}개년 중 {percentile}백분위 최장 연속 고립일수는 "
            f"{p:.1f}일입니다. 평균값({np.mean(values):.1f}일)이 아닌 상위 백분위를 "
            f"기준으로 삼은 이유는, 평년 수준으로 재고를 맞추면 기상이 특히 나빴던 "
            f"해(꼬리분포)에는 재고가 바닥나기 때문입니다. 여기에 안전 마진 1일을 "
            f"더해 {recommended}일분을 권고 안전재고로 제시합니다."
        ),
    }


def classify_current_status(hours_ok: dict, min_window_hours: int) -> dict:
    """
    특정 시점의 수단별 운용가능 여부를 '상태 등급'으로 분류.
    확률(%)을 만들어내지 않고, 근거 기반 상태 라벨만 반환. (35% 같은 표현 금지)
    """
    status = {}
    for mode, hrs in hours_ok.items():
        if hrs >= min_window_hours:
            label = "가능"
        elif hrs > 0:
            label = "제한적"
        else:
            label = "불가"
        status[mode] = {"label": label, "operational_hours": hrs}
    return status


def supply_window_recommendation(current_stock_days: float,
                                   recommended_safety_days: int,
                                   mode_status_today: dict,
                                   mode_status_24h: dict,
                                   mode_status_48h: dict) -> dict:
    """
    재고 + 수단별 상태(현재/+24h/+48h)를 결합해 선제보급 필요 여부를 판정.
    '최적 수단 추천'이 아니라 '실행 가능한 Window와 후보 수단 제시'로 표현.
    """
    any_available_today = any(s["label"] != "불가" for s in mode_status_today.values())
    degrading = (
        sum(s["label"] == "불가" for s in mode_status_48h.values()) >
        sum(s["label"] == "불가" for s in mode_status_today.values())
    )

    urgent = current_stock_days < recommended_safety_days

    candidate_modes_today = [m for m, s in mode_status_today.items() if s["label"] != "불가"]

    if urgent and any_available_today:
        action = "선제보급 권고 — 금일 실행"
    elif degrading and current_stock_days < recommended_safety_days * 1.5:
        action = "선제보급 검토 권고 — 48시간 내 창 축소 예상"
    else:
        action = "정상 — 별도 조치 불요"

    return {
        "현재재고_일수": current_stock_days,
        "권고_안전재고_일수": recommended_safety_days,
        "판정": action,
        "오늘_가용수단": candidate_modes_today,
        "48시간_내_창_축소_여부": degrading,
        "비고": "본 판정은 근거 기반 규칙(rule)이며 확률 예측이 아닙니다. 최종 결정은 지휘관 승인 필요.",
    }
