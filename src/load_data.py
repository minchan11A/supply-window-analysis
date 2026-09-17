"""
기상자료개방포털(data.kma.go.kr) ASOS/AWS 시간자료 로더
=========================================================
실제 사용 시:
  1) data.kma.go.kr → 기상관측 → 지상관측자료 → 시간자료
  2) 대상 부대 인근 관측지점(ASOS 또는 AWS) 선택, 최근 10년 CSV 다운로드
  3) 해당 CSV를 data/raw/ 에 넣고 아래 컬럼명 매핑만 실제 헤더에 맞게 조정

이 스크립트는 기상청 CSV의 대표적인 컬럼 구성을 기준으로 작성되었습니다.
(지점, 일시, 기온, 풍속, 풍향, 강수량, 시정 등)
컬럼명은 다운로드 시점의 포털 버전에 따라 다를 수 있어 COLUMN_MAP에서
한 곳만 고치면 나머지 파이프라인은 그대로 동작하도록 분리했습니다.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# 기상청 CSV 원본 컬럼명 → 내부 표준 컬럼명 매핑
# 2026년 기준 기상자료개방포털 ASOS 시간자료 실제 헤더에 맞춰 설정됨:
#   지점,지점명,일시,기온(°C),강수량(mm),풍속(m/s),풍향(16방위),습도(%),시정(10m)
COLUMN_MAP = {
    "일시": "datetime",
    "지점명": "station",
    "풍속(m/s)": "wind_mps",
    "풍속(m·s^-1)": "wind_mps",          # 포털 버전에 따른 표기 변형
    "최대순간풍속(m/s)": "gust_mps",      # 제공되지 않는 지점이 많음(선택)
    "최대순간풍속(m·s^-1)": "gust_mps",
    "시정(10m)": "visibility_10m",
    "강수량(mm)": "precip_mm",
    "기온(°C)": "temp_c",
    "풍향(16방위)": "wind_dir",
    "습도(%)": "humidity",
}


def load_kma_csv(filepath: str) -> pd.DataFrame:
    """
    기상청 시간자료 CSV 한 개를 표준 스키마로 로드.

    반환 컬럼: datetime, station, wind_mps, gust_mps, visibility_m, precip_mm
    """
    # 기상청 CSV는 EUC-KR(cp949) 인코딩
    df = pd.read_csv(filepath, encoding="cp949")

    # 컬럼명 정리 (공백 제거 후 매핑)
    df.columns = [c.strip() for c in df.columns]
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    required = ["datetime", "wind_mps"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"필수 컬럼 누락: {missing}. "
            f"COLUMN_MAP을 실제 CSV 헤더에 맞게 수정하세요. "
            f"현재 컬럼: {list(df.columns)}"
        )

    df["datetime"] = pd.to_datetime(df["datetime"])

    # 시정(10m 단위) → m 단위 환산
    if "visibility_10m" in df.columns:
        df["visibility_m"] = df["visibility_10m"] * 10
    elif "visibility_m" not in df.columns:
        df["visibility_m"] = np.nan

    # 최대순간풍속: 다수 지점에서 미제공 → 없으면 NaN으로 두고 판정에서 자동 제외
    if "gust_mps" not in df.columns:
        df["gust_mps"] = np.nan

    # ⚠ 강수량 결측 처리 주의:
    #   기상청 ASOS 시간자료에서 강수량 공란은 '측정 실패'가 아니라
    #   '무강수(비가 오지 않음)'를 의미합니다. 따라서 0으로 채우는 것이 옳습니다.
    #   (이를 NaN으로 두면 운용가능 판정에서 강수 조건이 통째로 무시됨)
    if "precip_mm" not in df.columns:
        df["precip_mm"] = 0.0
    df["precip_mm"] = df["precip_mm"].fillna(0.0)

    if "station" not in df.columns:
        df["station"] = "UNKNOWN"

    cols = ["datetime", "station", "wind_mps", "gust_mps", "visibility_m", "precip_mm"]
    return df[cols].sort_values("datetime").reset_index(drop=True)


def load_kma_directory(dirpath: str = "data/raw", pattern: str = "*.csv") -> pd.DataFrame:
    """
    폴더 안의 여러 CSV(연도별로 나눠 받은 파일)를 모두 읽어 하나로 병합.

    기상자료개방포털은 1회 다운로드 기간을 12개월로 제한하므로,
    10년치를 받으려면 연도별로 나눠 받게 됩니다.
    그 파일들을 data/raw/ 에 모두 넣어두고 이 함수를 쓰면 자동 병합됩니다.

    중복 시각(파일 경계에서 겹치는 행)은 제거합니다.
    """
    files = sorted(Path(dirpath).glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"{dirpath} 에 CSV 파일이 없습니다. 기상청에서 받은 파일을 넣어주세요."
        )

    frames = []
    for f in files:
        try:
            frames.append(load_kma_csv(str(f)))
        except Exception as e:
            print(f"  [경고] {f.name} 읽기 실패 — 건너뜁니다: {e}")

    if not frames:
        raise ValueError("읽을 수 있는 CSV가 하나도 없습니다.")

    merged = pd.concat(frames, ignore_index=True)
    before = len(merged)
    merged = (
        merged.drop_duplicates(subset=["datetime"])
        .sort_values("datetime")
        .reset_index(drop=True)
    )
    removed = before - len(merged)

    print(f"  병합: {len(files)}개 파일 → {len(merged):,} 행"
          f"{f' (중복 {removed}행 제거)' if removed else ''}")
    return merged


def generate_synthetic_data(
    station: str = "가상_도서관측소",
    start: str = "2016-01-01",
    end: str = "2025-12-31",
    seed: int = 42,
    storms_per_winter: tuple = (3, 6),
    storm_duration_days: tuple = (1, 4),
) -> pd.DataFrame:
    """
    실제 데이터가 없을 때 파이프라인 검증용 합성(가상) 기상자료를 생성.

    설계 원칙:
      - 배경 풍속에 계절성(겨울철 상승)과 일중 패턴을 반영
      - 여기에 더해, 겨울철(11~3월) 동안 연 3~6회의 '폭풍 이벤트'를
        1~4일 지속시간으로 명시적으로 주입 (자기상관된 고풍속 구간)
      - 이렇게 해야 '전수단 동시 불가일'이 현실적인 빈도로 발생해
        고립일수 트렌드·캘린더 히트맵이 검증 가능한 형태로 나옴

    ⚠ 이 함수는 데모/테스트 전용입니다. 파이프라인이 올바르게 동작하는지
       확인하기 위한 것이며, 실제 제안서 제출 시에는 반드시
       load_kma_csv()로 실측 데이터를 넣어 교체해야 합니다.
       (수치 자체에는 아무런 실증적 의미가 없습니다)
    """
    rng = np.random.default_rng(seed)
    dt_index = pd.date_range(start=start, end=end, freq="h")
    n = len(dt_index)

    day_of_year = dt_index.dayofyear.values
    hour = dt_index.hour.values
    year = dt_index.year.values

    # 배경 계절성: 겨울(12~2월)에 평균풍속 상승
    seasonal = 3.0 + 2.0 * np.cos(2 * np.pi * (day_of_year - 30) / 365)
    # 일중 패턴: 오후에 풍속 약간 상승
    diurnal = 0.6 * np.sin(2 * np.pi * (hour - 6) / 24)
    noise = rng.gamma(shape=2.0, scale=0.9, size=n)
    wind = np.clip(seasonal + diurnal + noise - 1.5, 0, None)

    precip = rng.choice([0, 0, 0, 0, 0, 1, 3, 8], size=n,
                         p=[0.75, 0.06, 0.05, 0.04, 0.03, 0.03, 0.02, 0.02])

    # ── 폭풍 이벤트 명시적 주입 (겨울철 집중) ──
    storm_boost_wind = np.zeros(n)
    storm_boost_precip = np.zeros(n)
    dt_series = pd.Series(dt_index)

    for yr in np.unique(year):
        # 해당 winter season: 그 해 11~12월 + 다음해 1~3월을 하나의 '겨울'로 취급
        n_storms = rng.integers(storms_per_winter[0], storms_per_winter[1] + 1)
        winter_candidates = dt_series[
            ((dt_series.dt.year == yr) & (dt_series.dt.month.isin([11, 12]))) |
            ((dt_series.dt.year == yr + 1) & (dt_series.dt.month.isin([1, 2, 3])))
        ]
        if winter_candidates.empty:
            continue

        for _ in range(n_storms):
            start_ts = winter_candidates.sample(1, random_state=rng.integers(0, 1_000_000)).iloc[0]
            duration_h = int(rng.integers(storm_duration_days[0], storm_duration_days[1] + 1) * 24)
            mask = (dt_index >= start_ts) & (dt_index < start_ts + pd.Timedelta(hours=duration_h))

            # 폭풍 강도: 사다리꼴 프로파일(초반 15%/후반 15% 램프, 중간 70% 고원 유지)
            # → 종형(hanning)보다 정점 구간이 오래 지속되어, 실제 '전일 불가'가
            #    현실적인 빈도로 발생하도록 함
            idx = np.where(mask)[0]
            m = len(idx)
            if m == 0:
                continue
            ramp = max(1, int(m * 0.15))
            profile = np.ones(m)
            profile[:ramp] = np.linspace(0, 1, ramp)
            profile[-ramp:] = np.linspace(1, 0, ramp)

            peak_intensity = rng.uniform(9, 18)
            storm_boost_wind[idx] += profile * peak_intensity
            storm_boost_precip[idx] += profile * rng.uniform(5, 25)

    wind = wind + storm_boost_wind
    precip = precip + storm_boost_precip
    gust = wind * rng.uniform(1.25, 1.6, size=n)

    # 시정: 강풍/강수와 음의 상관 (폭풍 중에는 크게 저하)
    visibility = np.clip(
        20000 - wind * 500 - precip * 250 + rng.normal(0, 1200, n), 100, 20000
    )

    df = pd.DataFrame({
        "datetime": dt_index,
        "station": station,
        "wind_mps": wind.round(1),
        "gust_mps": gust.round(1),
        "visibility_m": visibility.round(0),
        "precip_mm": precip.round(1),
    })
    return df


if __name__ == "__main__":
    # 간단 셀프테스트
    df = generate_synthetic_data()
    print(df.head())
    print(f"\n생성된 레코드 수: {len(df):,}")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
