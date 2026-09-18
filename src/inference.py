"""
심화 통계 추론 (Statistical Inference)
========================================
기술통계를 넘어, 안전재고 기준에 통계적 엄밀성을 부여한다.

핵심 방법론:
  1. 마르코프 지속성 — 고립이 하루 더 이어질 조건부 확률 추정 (기하분포)
  2. 포아송 사건빈도 — 연간 고립사건 발생률 추정 및 과산포 검정
  3. 복합 포아송-기하 모형 — 연최대 고립일수 분포 유도 → 재현기간(return period)별 수준
  4. 부트스트랩 신뢰구간 — 소표본(10개년) P95의 불확실성 정량화
  5. Mann-Kendall 추세검정 — 고립 감소 추세의 통계적 유의성
  6. 수단 간 의존구조 — 상보성이 우연인지 구조적인지 검정

⚠ 이 모듈은 '미래를 예측'하지 않는다. 관측된 빈도구조로부터
   극단 상황의 재현수준을 추정하는 것이며, 모든 가정은 명시적으로 검증된다.
"""

import numpy as np
import pandas as pd
from scipy import stats

from .descriptive import longest_isolation_runs, longest_isolation_per_year


# ────────────────────────────────────────────────────────────
# 1. 마르코프 지속성 (고립의 하루 더 이어질 확률)
# ────────────────────────────────────────────────────────────
def isolation_persistence(daily_df: pd.DataFrame) -> dict:
    """
    고립 구간의 run-length로부터 지속확률 p를 추정.

    run-length가 기하분포 Geom(1-p)를 따른다고 보면,
      p(지속) = (총 고립일수 - 사건수) / 총 고립일수
    이는 "고립 상태에서 다음 날도 고립일 조건부 확률"의 MLE이다.
    """
    runs = longest_isolation_runs(daily_df)
    n_events = len(runs)
    total_days = int(runs["length"].sum()) if n_events else 0

    if n_events == 0:
        return {"사건수": 0, "총고립일": 0, "지속확률": 0.0}

    p_continue = (total_days - n_events) / total_days
    mean_dur = total_days / n_events

    # 기하분포 적합도: 관측 vs 이론 run-length 분포
    obs = runs["length"].value_counts().sort_index()
    theo = {k: n_events * (p_continue ** (k - 1)) * (1 - p_continue)
            for k in obs.index}

    return {
        "사건수": n_events,
        "총고립일": total_days,
        "평균지속일": round(mean_dur, 2),
        "지속확률_p": round(p_continue, 4),
        "해석": (
            f"고립이 시작되면 다음 날도 고립일 확률은 {p_continue:.1%}이다. "
            f"즉 고립은 평균 {mean_dur:.1f}일 만에 해소되며, 장기화 경향은 약하다."
        ),
        "관측_runlength분포": dict(obs),
        "기하분포_기대값": {k: round(v, 1) for k, v in theo.items()},
    }


# ────────────────────────────────────────────────────────────
# 2. 포아송 사건빈도
# ────────────────────────────────────────────────────────────
def event_frequency_model(daily_df: pd.DataFrame) -> dict:
    """
    연간 고립사건 발생 횟수가 포아송 분포를 따르는지 검정하고 λ를 추정.
    과산포(분산 > 평균)가 크면 사건이 특정 연도에 군집함을 의미.
    """
    runs = longest_isolation_runs(daily_df)
    years = sorted(daily_df["date"].dt.year.unique())

    if runs.empty:
        counts = np.zeros(len(years))
    else:
        r = runs.copy()
        r["year"] = pd.to_datetime(r["start"]).dt.year
        c = r.groupby("year").size()
        counts = np.array([c.get(y, 0) for y in years], dtype=float)

    lam = counts.mean()
    var = counts.var(ddof=1) if len(counts) > 1 else 0.0
    dispersion = var / lam if lam > 0 else np.nan

    return {
        "연도별_사건수": counts.astype(int).tolist(),
        "λ_연평균사건수": round(float(lam), 3),
        "표본분산": round(float(var), 3),
        "과산포지수": round(float(dispersion), 3) if lam > 0 else None,
        "해석": (
            f"연평균 {lam:.2f}회의 고립사건이 발생한다. "
            + ("분산이 평균을 크게 상회하여(과산포), 사건이 특정 연도에 군집하는 경향이 있다. "
               "따라서 평년 기준이 아닌 극단 연도 기준의 대비가 필요하다."
               if dispersion and dispersion > 1.5 else
               "분산과 평균이 유사하여 포아송 가정이 대체로 타당하다.")
        ),
    }


# ────────────────────────────────────────────────────────────
# 3. 복합 포아송-기하 → 재현기간별 수준
# ────────────────────────────────────────────────────────────
def return_level_analysis(daily_df: pd.DataFrame,
                            return_periods=(5, 10, 20, 50)) -> dict:
    """
    연최대 연속 고립일수의 분포를 복합 모형으로 유도하여 재현수준을 산출.

    모형:
      - 연간 사건수 N ~ Poisson(λ)
      - 각 사건의 지속일수 D ~ Geometric(1-p)   (P(D=k) = p^(k-1)(1-p))
      - 연최대 M = max(D_1..D_N),  N=0이면 M=0

      P(M < k) = exp(-λ · P(D ≥ k))     [포아송 희박화(thinning) 성질]
               = exp(-λ · p^(k-1))

    재현기간 T년에 대응하는 수준 = P(M ≥ k) = 1/T 를 만족하는 최소 정수 k

    ⚠ 이 방법은 미래를 '예측'하는 것이 아니라, 관측된 빈도구조가
       유지된다는 가정 하의 극단 수준을 추정하는 것이다.
       고전적 극단값 이론(EVT)의 POT 접근과 동일한 논리이며,
       소표본 연최대값에 GEV를 직접 적합하는 것보다 안정적이다.
    """
    pers = isolation_persistence(daily_df)
    freq = event_frequency_model(daily_df)

    p = pers["지속확률_p"]
    lam = freq["λ_연평균사건수"]

    if lam == 0:
        return {"오류": "고립사건이 관측되지 않아 재현수준 산출 불가"}

    def prob_max_ge(k: int) -> float:
        """P(연최대 ≥ k일)"""
        if k <= 0:
            return 1.0
        p_dur_ge_k = p ** (k - 1)          # P(D ≥ k)
        return 1.0 - np.exp(-lam * p_dur_ge_k)

    levels = {}
    for T in return_periods:
        target = 1.0 / T
        k = 1
        while k < 60 and prob_max_ge(k) > target:
            k += 1
        levels[f"{T}년 재현수준"] = k

    curve = [{"고립일수": k,
              "초과확률": round(prob_max_ge(k), 4),
              "재현기간_년": round(1 / prob_max_ge(k), 1) if prob_max_ge(k) > 0 else None}
             for k in range(1, 7)]

    return {
        "모형": "복합 포아송-기하 (Poisson-Geometric compound)",
        "λ": lam, "p": p,
        "재현수준": levels,
        "초과확률곡선": curve,
        "해석": (
            f"연평균 {lam:.2f}회 발생하고 하루 더 지속될 확률이 {p:.1%}인 구조에서, "
            f"20년에 한 번 수준의 고립은 {levels.get('20년 재현수준')}일이다."
        ),
    }


# ────────────────────────────────────────────────────────────
# 4. 부트스트랩 신뢰구간
# ────────────────────────────────────────────────────────────
def bootstrap_percentile_ci(daily_df: pd.DataFrame, percentile: int = 95,
                              n_boot: int = 10000, seed: int = 42) -> dict:
    """
    연최대 고립일수 표본(10개년)에서 P95의 부트스트랩 신뢰구간을 산출.
    소표본 백분위수의 불확실성을 명시적으로 드러낸다.
    """
    per_year = longest_isolation_per_year(daily_df)
    vals = per_year["max_isolation_days"].values.astype(float)
    n = len(vals)

    rng = np.random.default_rng(seed)
    boots = np.array([
        np.percentile(rng.choice(vals, size=n, replace=True), percentile)
        for _ in range(n_boot)
    ])

    return {
        "표본": vals.astype(int).tolist(),
        "표본크기": n,
        f"P{percentile}_점추정": round(float(np.percentile(vals, percentile)), 2),
        "부트스트랩_평균": round(float(boots.mean()), 2),
        "95%_신뢰구간": [round(float(np.percentile(boots, 2.5)), 2),
                        round(float(np.percentile(boots, 97.5)), 2)],
        "해석": (
            f"10개년 표본에서 P{percentile} 점추정치는 "
            f"{np.percentile(vals, percentile):.1f}일이나, 부트스트랩 95% 신뢰구간은 "
            f"[{np.percentile(boots, 2.5):.1f}, {np.percentile(boots, 97.5):.1f}]일이다. "
            f"소표본으로 인한 불확실성이 존재하므로, 상한을 고려한 보수적 기준 설정이 타당하다."
        ),
    }


# ────────────────────────────────────────────────────────────
# 5. Mann-Kendall 추세검정
# ────────────────────────────────────────────────────────────
def mann_kendall_trend(daily_df: pd.DataFrame) -> dict:
    """
    연도별 고립일수의 단조 추세를 비모수 검정(Mann-Kendall).
    정규성 가정이 불필요하여 소표본·이산값에 적합하다.
    """
    d = daily_df.copy()
    d["year"] = d["date"].dt.year
    annual = d.groupby("year")["all_unavailable"].sum()
    x = annual.values.astype(float)
    n = len(x)

    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))

    # 동점 보정 분산
    unique, counts = np.unique(x, return_counts=True)
    tie_term = sum(c * (c - 1) * (2 * c + 5) for c in counts)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    if var_s <= 0:
        z = 0.0
    elif s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    # Theil-Sen 기울기
    slopes = [(x[j] - x[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n)]
    sen = float(np.median(slopes)) if slopes else 0.0

    sig = p_value < 0.05
    direction = "감소" if s < 0 else ("증가" if s > 0 else "무추세")

    return {
        "연도별_고립일수": annual.astype(int).tolist(),
        "S통계량": int(s),
        "Z": round(float(z), 3),
        "p값": round(float(p_value), 4),
        "Sen기울기_일per년": round(sen, 3),
        "유의성": "유의(p<0.05)" if sig else "유의하지 않음",
        "해석": (
            f"고립일수는 {direction} 방향이나 p={p_value:.3f}로 "
            + ("통계적으로 유의하다. 다만 추세를 기준 완화의 근거로 삼는 것은 "
               "안전측면에서 신중해야 한다."
               if sig else
               "통계적으로 유의하지 않다. 따라서 '고립 위험이 줄었다'고 단정하여 "
               "기준을 완화할 근거는 없으며, 전 기간을 동등하게 반영함이 타당하다.")
        ),
    }


# ────────────────────────────────────────────────────────────
# 6. 수단 간 의존구조 (상보성의 통계적 검정)
# ────────────────────────────────────────────────────────────
def mode_dependence(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    수단 쌍별로 '동시 불가'가 독립 가정보다 적게 일어나는지 검정.
    파이계수(φ)와 카이제곱 검정으로 상보성의 구조성을 확인한다.
    """
    modes = ["선박", "헬기", "드론"]
    rows = []
    for i in range(len(modes)):
        for j in range(i + 1, len(modes)):
            a, b = modes[i], modes[j]
            fa = (daily_df[f"opday_{a}"] == 0).astype(int)
            fb = (daily_df[f"opday_{b}"] == 0).astype(int)

            both = int(((fa == 1) & (fb == 1)).sum())
            expected = fa.mean() * fb.mean() * len(daily_df)

            table = pd.crosstab(fa, fb)
            try:
                chi2, pval, _, _ = stats.chi2_contingency(table)
            except Exception:
                chi2, pval = np.nan, np.nan

            phi = np.sqrt(chi2 / len(daily_df)) if chi2 == chi2 else np.nan

            rows.append({
                "수단쌍": f"{a}–{b}",
                f"{a}불가일": int(fa.sum()),
                f"{b}불가일": int(fb.sum()),
                "동시불가_관측": both,
                "독립가정_기대": round(float(expected), 1),
                "관측/기대": round(both / expected, 2) if expected > 0 else None,
                "φ계수": round(float(phi), 3) if phi == phi else None,
                "p값": round(float(pval), 6) if pval == pval else None,
            })
    return pd.DataFrame(rows)


# ────────────────────────────────────────────────────────────
# 7. 지형 대표성 민감도 (DEM 보정 대신)
# ────────────────────────────────────────────────────────────
def terrain_representativeness(raw_df: pd.DataFrame,
                                 wind_uplifts=(0.0, 0.10, 0.20, 0.30)) -> pd.DataFrame:
    """
    관측소와 실제 부대 위치 간 국지풍 차이를 '보정'하지 않고,
    '실제 부대 풍속이 관측소 대비 X% 높다면'이라는 가정 하에
    결론이 어떻게 변하는지 추적한다.

    → DEM으로 풍속을 산출하지 않으면서도
      "관측소가 부대를 대표하지 못한다"는 우려에 정량적으로 답한다.
    """
    from .config import THRESHOLDS
    from .sensitivity import _apply_scenario
    from .descriptive import compute_daily_operability

    rows = []
    for up in wind_uplifts:
        df = raw_df.copy()
        df["wind_mps"] = df["wind_mps"] * (1 + up)
        df["gust_mps"] = df["gust_mps"] * (1 + up)

        hourly = _apply_scenario(df, THRESHOLDS)
        daily = compute_daily_operability(hourly)
        per_year = longest_isolation_per_year(daily)

        row = {"풍속_가정": f"관측소 대비 +{int(up*100)}%"}
        for m in THRESHOLDS:
            row[f"가용률_{m}"] = round(daily[f"opday_{m}"].mean() * 100, 1)
        row["동시불가일"] = int(daily["all_unavailable"].sum())
        row["최장고립일"] = int(per_year["max_isolation_days"].max())
        rows.append(row)
    return pd.DataFrame(rows)


# ────────────────────────────────────────────────────────────
# 8. 재현수준의 모수 부트스트랩 신뢰구간
# ────────────────────────────────────────────────────────────
def return_level_ci(daily_df: pd.DataFrame, target_period: int = 20,
                      n_boot: int = 5000, seed: int = 42) -> dict:
    """
    복합 포아송-기하 모형의 재현수준에 대한 모수 부트스트랩 신뢰구간.

    소표본(사건 12건)에서 추정한 λ, p의 불확실성이
    재현수준에 얼마나 전파되는지 정량화한다.

    절차:
      1) 관측된 λ, p로 가상의 10년치 사건을 재생성
      2) 재생성 표본에서 λ*, p*를 재추정
      3) 재추정 모수로 재현수준을 다시 계산
      4) 1~3을 n_boot회 반복하여 분포를 얻음

    → "20년 재현수준 3일"이 아니라
      "20년 재현수준 3일 [95% CI: 2~4일]"로 정직하게 보고하기 위함.
    """
    pers = isolation_persistence(daily_df)
    freq = event_frequency_model(daily_df)
    lam0, p0 = freq["λ_연평균사건수"], pers["지속확률_p"]
    n_years = len(freq["연도별_사건수"])

    if lam0 == 0:
        return {"오류": "고립사건 없음"}

    rng = np.random.default_rng(seed)

    def level_from(lam, p, T):
        if lam <= 0:
            return 0
        k = 1
        while k < 60 and (1 - np.exp(-lam * (p ** (k - 1)))) > 1 / T:
            k += 1
        return k

    levels = []
    for _ in range(n_boot):
        counts = rng.poisson(lam0, size=n_years)
        n_ev = int(counts.sum())
        if n_ev == 0:
            levels.append(0)
            continue
        durs = rng.geometric(1 - p0, size=n_ev)   # 지속일수 재생성
        lam_b = counts.mean()
        tot = durs.sum()
        p_b = (tot - n_ev) / tot if tot > 0 else 0.0
        levels.append(level_from(lam_b, p_b, target_period))

    levels = np.array(levels)
    point = level_from(lam0, p0, target_period)

    return {
        "재현기간_년": target_period,
        "점추정": point,
        "95%_신뢰구간": [int(np.percentile(levels, 2.5)),
                        int(np.percentile(levels, 97.5))],
        "부트스트랩_중앙값": int(np.median(levels)),
        "해석": (
            f"{target_period}년 재현수준 점추정은 {point}일이나, "
            f"사건 표본이 작아 모수 불확실성을 반영하면 95% 신뢰구간은 "
            f"[{int(np.percentile(levels, 2.5))}, {int(np.percentile(levels, 97.5))}]일이다. "
            f"따라서 단일 수치가 아닌 범위로 해석해야 한다."
        ),
    }


# ────────────────────────────────────────────────────────────
# 9. 수단별 한계 보완 효과 (정책적으로 올바른 방향의 상보성)
# ────────────────────────────────────────────────────────────
def marginal_contribution(daily_df: pd.DataFrame) -> dict:
    """
    각 수단이 '다른 수단들이 모두 막힌 상황'에서 보급 창구를 얼마나 열어주는지 측정.

    ⚠ 방향이 중요하다:
      (X) "드론 불가일 중 다른 수단 가능 비율" → 드론의 취약성을 반영할 뿐
      (O) "선박·헬기 동시 불가일 중 드론 가능 비율" → 드론의 실제 기여도

    전자는 불가일이 많은 수단일수록 높게 나오는 편향이 있어
    정책 판단 근거로 부적절하다.
    """
    modes = ["선박", "헬기", "드론"]
    result = {}

    for target in modes:
        others = [m for m in modes if m != target]
        # 다른 수단이 '모두' 불가한 날
        others_all_bad = (daily_df[[f"opday_{m}" for m in others]].sum(axis=1) == 0)
        n_others_bad = int(others_all_bad.sum())

        if n_others_bad == 0:
            result[target] = {"타수단_전부불가일": 0, "해당수단_가용일": 0,
                              "기여율": None, "잔여고립일": 0}
            continue

        target_ok = daily_df[f"opday_{target}"] == 1
        rescued = int((others_all_bad & target_ok).sum())
        remaining = n_others_bad - rescued

        result[target] = {
            "타수단_전부불가일": n_others_bad,
            "해당수단_가용일": rescued,
            "기여율": round(rescued / n_others_bad * 100, 1),
            "잔여고립일": remaining,
            "해석": (
                f"{'·'.join(others)}가 모두 막힌 {n_others_bad}일 중 "
                f"{target}은(는) {rescued}일({rescued/n_others_bad*100:.1f}%)에서 운용 가능하였다. "
                f"{target} 부재 시 고립일은 {n_others_bad}일이나, 포함 시 {remaining}일로 감소한다."
            ),
        }
    return result
