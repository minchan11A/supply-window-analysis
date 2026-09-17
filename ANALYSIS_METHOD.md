# 보급윈도우 분석 — 코드 동작 설명서

> 이 문서는 "어떤 데이터를, 어떤 코드로, 어떻게 분석했는가"를 처음부터 끝까지 설명합니다.
> 심사 질의응답에서 어떤 질문이 와도 답할 수 있도록, 각 단계의 **왜**까지 함께 적었습니다.

---

## 0. 전체 그림 — 데이터가 흘러가는 경로

```
[입력] 기상청 CSV 10개 (연도별)
   │    각 8,760행 (1년 × 24시간)
   ▼
① load_data.py     ── 병합 + 전처리 → 87,432행
   ▼
② descriptive.py   ── 시간별 판정 → 일별 집계 → 3,643일
   ▼
③ diagnostic.py    ── 원인 분해, 계절성
   ▼
④ inference.py     ── 확률모형, 재현기간, 검정
   ▼
⑤ sensitivity.py   ── 임계값 흔들어보기
   ▼
⑥ visualize.py     ── 그래프 7장
   ▼
[출력] CSV 6개 + JSON 1개 + PNG 7장
```

실행 명령은 한 줄입니다.

```bash
python run_analysis.py --dir data/raw --station "백령도"
```

---

## 1. 입력 데이터 — 무엇을 받았나

기상청 기상자료개방포털(data.kma.go.kr)의 **종관기상관측(ASOS) 시간자료**입니다.

| 항목 | 내용 |
|---|---|
| 지점 | 백령도 (지점번호 102) |
| 기간 | 2016.01.01 ~ 2025.12.31 (10년) |
| 파일 | `asos_2016.csv` ~ `asos_2025.csv` (10개) |
| 원본 행 수 | 각 8,760행 → 합계 87,432행 |

**실제 CSV 헤더** (인코딩: CP949/EUC-KR)

```
지점,지점명,일시,기온(°C),강수량(mm),풍속(m/s),풍향(16방위),습도(%),시정(10m)
102,백령도,2016-01-01 01:00,2.4,,3.3,270,62,2000
```

이 중 **풍속, 시정, 강수량** 3개를 사용했습니다. (최대순간풍속은 이 지점에서 제공되지 않음)

> **왜 ASOS인가?** AWS(방재기상관측)는 도서·산간에 더 촘촘하지만 **대부분 시정을 관측하지 않습니다.**
> 분석 결과 시정이 보급 제약의 지배 요인으로 드러났으므로, 이 선택이 결정적이었습니다.

---

## 2. 전처리 — `src/load_data.py`

### 2-1. 컬럼명 매핑

기상청 헤더는 포털 버전에 따라 표기가 조금씩 다릅니다(`풍속(m/s)` vs `풍속(m·s^-1)`).
그래서 **매핑 딕셔너리 한 곳**만 고치면 나머지가 전부 동작하도록 분리했습니다.

```python
COLUMN_MAP = {
    "일시": "datetime",
    "지점명": "station",
    "풍속(m/s)": "wind_mps",
    "시정(10m)": "visibility_10m",
    "강수량(mm)": "precip_mm",
    ...
}
```

### 2-2. 시정 단위 환산

기상청은 시정을 **10m 단위**로 줍니다. `2000` = 20,000m = 20km.

```python
df["visibility_m"] = df["visibility_10m"] * 10
```

### 2-3. 강수량 결측 처리 — 여기가 중요합니다

원본 CSV에서 강수량 칸은 **8,039행이 비어 있습니다**(1년 기준). 이걸 "측정 실패"로 보면 안 됩니다.

> **기상청 ASOS에서 강수량 공란은 '비가 오지 않음'을 의미합니다.**

```python
df["precip_mm"] = df["precip_mm"].fillna(0.0)
```

만약 이걸 결측(NaN)으로 두면, 판정 로직에서 강수 조건이 **통째로 무시**되어 분석이 왜곡됩니다.

### 2-4. 10개 파일 병합

포털이 한 번에 12개월까지만 받게 해서 연도별로 나눠 받았습니다. 폴더를 통째로 읽어 합칩니다.

```python
def load_kma_directory(dirpath="data/raw"):
    files = sorted(Path(dirpath).glob("*.csv"))
    frames = [load_kma_csv(str(f)) for f in files]
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["datetime"]).sort_values("datetime")
    return merged
```

파일 경계에서 시각이 겹치면 `drop_duplicates`로 제거합니다.

---

## 3. 운용 가능 판정 — `src/config.py` + `src/descriptive.py`

### 3-1. 임계값 정의 (`config.py`)

각 수단이 "언제 못 뜨는가"를 한 곳에 모아 관리합니다.

```python
THRESHOLDS = {
    "선박": ModeThreshold(max_wind_mps=14.0, min_visibility_m=1000, max_precip_mm_h=15.0, ...),
    "헬기": ModeThreshold(max_wind_mps=15.0, min_visibility_m=1600, max_precip_mm_h=10.0, ...),
    "드론": ModeThreshold(max_wind_mps=8.0,  min_visibility_m=500,  max_precip_mm_h=3.0,  ...),
}
MIN_OPERATIONAL_WINDOW_HOURS = 6   # 하루 중 6시간 이상 가능해야 '운용가능일'
SAFETY_STOCK_PERCENTILE = 95       # 안전재고 산정 백분위
```

> ⚠ 이 수치는 **예시값**입니다. 실제 교범값으로 바꾸면 결과가 자동 갱신됩니다.
> (그래서 6장 민감도 분석으로 "바뀌어도 결론은 같다"를 증명했습니다)

### 3-2. 시간 단위 판정

87,432행 각각에 대해 "이 시각에 이 수단이 뜰 수 있나"를 판정합니다.

```python
def is_hour_operational(row, mode):
    th = THRESHOLDS[mode]
    ok = True
    if not pd.isna(row["wind_mps"]):
        ok &= row["wind_mps"] <= th.max_wind_mps          # 풍속이 한계 이하
    if not pd.isna(row["visibility_m"]):
        ok &= row["visibility_m"] >= th.min_visibility_m  # 시정이 최소 이상
    if not pd.isna(row["precip_mm"]):
        ok &= row["precip_mm"] <= th.max_precip_mm_h      # 강수가 한계 이하
    return bool(ok)
```

**결측 안전 설계**: `pd.isna()` 체크가 있어서, 최대순간풍속처럼 **데이터가 없는 변수는 자동으로 조건에서 빠집니다.**
그래서 이 지점에 돌풍 자료가 없어도 에러 없이 돌아갑니다.

결과: 87,432행 × 3수단 = **262,296회의 판정**.

### 3-3. 일 단위 집계 — "하루 6시간" 규칙

시간별 판정을 날짜로 묶습니다. 핵심은 **"몇 시간 가능해야 그날 보급이 되는가"** 입니다.

```python
for date, g in df.groupby("date"):
    hours_ok = g[f"op_{mode}"].sum()                      # 그날 가능한 시간 수
    row[f"opday_{mode}"] = int(hours_ok >= 6)             # 6시간 이상이면 운용가능일
```

> **왜 6시간인가?** 1시간만 창이 열려서는 출항 준비·항해·하역·복귀가 불가능합니다.
> 실제 보급 작업에 필요한 최소 시간을 반영한 값이며, `config.py`에서 조정 가능합니다.

### 3-4. 관측 커버리지 필터 — 실제로 버그를 잡은 부분

처음 돌렸을 때 **매년 12월 31일이 고립일로 잡히는** 이상 현상이 있었습니다.

원인은 기상이 아니라 데이터 구조였습니다. 포털에서 연도별로 받으면 각 파일이
`01-01 01:00 ~ 12-31 00:00`으로 끝나서, **12월 31일에 관측치가 단 1시간**뿐입니다.
6시간 기준을 못 채우니 자동으로 '불가' 판정된 것입니다.

```python
if len(g) < min_coverage_hours:   # 하루 관측이 18시간 미만이면
    excluded += 1
    continue                       # 분석에서 제외
```

**이 필터 하나로 고립사건 22건 → 12건으로 정정**되었고,
"12월 집중"이라는 잘못된 결론이 사라지고 **7월 해무철 집중**이라는 진짜 패턴이 드러났습니다.

> 심사에서 "데이터 검증은 했나"라고 물으면 이 사례를 말씀하시면 됩니다. 강력한 답변입니다.

### 3-5. 전수단 동시불가일

```python
daily["all_unavailable"] = (daily[["opday_선박","opday_헬기","opday_드론"]].sum(axis=1) == 0).astype(int)
```

3개 수단의 합이 0이면 = 전부 막힌 날 = **고립일**입니다. 결과는 **15일 / 3,643일 (0.41%)**.

### 3-6. 연속 고립 구간(run-length) 계산

"며칠 연속 고립됐나"를 세는 방법입니다. 판다스의 전형적인 관용구를 씁니다.

```python
df["group"] = (df["all_unavailable"] != df["all_unavailable"].shift()).cumsum()
runs = df[df["all_unavailable"]==1].groupby("group").agg(
    start=("date","min"), end=("date","max"), length=("date","count"))
```

**작동 원리**: 값이 바뀌는 지점마다 `cumsum()`이 증가하므로, 연속된 같은 값끼리 같은 그룹 번호를 갖습니다.
그 그룹을 세면 연속 길이가 나옵니다.

결과: **12건의 고립사건, 최장 2일**.

---

## 4. 원인 분해 — `src/diagnostic.py`

"못 뜬 시간 중 무엇 때문이었나"를 셉니다.

```python
unavailable = hourly_df[hourly_df[f"op_{mode}"] == False]
factors = {
    "평균풍속 초과": (unavailable["wind_mps"] > th.max_wind_mps).sum(),
    "시정 불량":    (unavailable["visibility_m"] < th.min_visibility_m).sum(),
    "강수 과다":    (unavailable["precip_mm"] > th.max_precip_mm_h).sum(),
}
share = count / len(unavailable)
```

> **중복 계상에 주의**: 강풍과 안개가 동시에 온 시간은 두 요인 모두에 카운트됩니다.
> 그래서 비중 합이 100%를 넘을 수 있고, 그래프도 **누적막대가 아닌 그룹막대**로 그렸습니다.
> (처음엔 누적으로 그렸다가 합이 2.4가 나와서 잘못을 발견하고 수정)

**결과**: 선박 시정 94.9% / 헬기 97.2% / **드론만 풍속 61.9%** — 이 비대칭이 상보성의 근원입니다.

---

## 5. 통계 추론 — `src/inference.py` (가장 기술적인 부분)

여기가 "엑셀 필터링 아니냐"는 비판에 대한 답입니다.

### 5-1. 마르코프 지속확률

고립이 하루 더 이어질 조건부 확률을 추정합니다.

```python
p_continue = (총고립일수 - 사건수) / 총고립일수
           = (15 - 12) / 15 = 0.20
```

**원리**: 고립 구간 길이가 기하분포를 따른다고 보면, 위 식이 지속확률의 최대우도추정치(MLE)입니다.
직관적으로는 "15일의 고립일 중 12번은 그날로 끝났고 3번은 이어졌다"는 뜻입니다.

적합도 확인: 관측 run-length `{1일: 9건, 2일: 3건}` vs 기하분포 기대값 `{1일: 9.6, 2일: 1.9}` — 잘 맞습니다.

### 5-2. 포아송 사건빈도 + 과산포 진단

```python
lam = counts.mean()        # 1.20회/년
var = counts.var(ddof=1)   # 3.511
dispersion = var / lam     # 2.93
```

**과산포지수 2.93**이 중요합니다. 포아송이면 분산≈평균(지수≈1)이어야 하는데 3배 가까이 큽니다.
= **사건이 특정 연도에 몰린다**(2016년 5회, 2019년 이후 대부분 0회).
= 평년 기준으로 재고를 잡으면 안 되고 **극단 연도를 기준으로 잡아야 한다**는 근거입니다.

### 5-3. 복합 포아송-기하 모형 → 재현기간

이 제안서에서 가장 수학적인 부분입니다.

**모형 설정**
- 연간 사건 수: `N ~ Poisson(λ=1.20)`
- 각 사건 지속일수: `D ~ Geometric(1-p), p=0.20`
- 연최대 고립일수: `M = max(D₁...D_N)`, 사건이 없으면 0

**유도**

포아송 과정의 희박화(thinning) 성질에 의해, "k일 이상 지속되는 사건"만 뽑으면
그것도 포아송이고 그 발생률은 `λ · P(D ≥ k)` 입니다.

기하분포에서 `P(D ≥ k) = p^(k-1)` 이므로,

```
P(M < k) = P(k일 이상 사건이 0건) = exp(-λ · p^(k-1))
P(M ≥ k) = 1 - exp(-λ · p^(k-1))
```

**코드**

```python
def prob_max_ge(k):
    p_dur_ge_k = p ** (k - 1)
    return 1.0 - np.exp(-lam * p_dur_ge_k)

# 재현기간 T년 = 초과확률 1/T 가 되는 k를 찾음
for T in (5, 10, 20, 50):
    k = 1
    while prob_max_ge(k) > 1/T:
        k += 1
    levels[T] = k
```

**결과**

| 고립일수 | 초과확률 | 재현기간 |
|---|---|---|
| 2일 | 21.3% | 4.7년 |
| **3일** | **4.7%** | **21.3년** |
| 4일 | 0.96% | 104.7년 |

> **핵심**: 백분위 방식(P95+1일)으로 얻은 **3일분**이, 전혀 다른 경로인 재현기간 분석에서도
> **20년 재현수준 3일**과 일치합니다. 두 독립 방법의 수렴이 기준값의 타당성을 교차 검증합니다.

이 기법은 수문학에서 **확률강우량·계획홍수위**를 정할 때 쓰는 표준 방법(POT, Peaks-Over-Threshold)과
같은 계열입니다. 소표본 연최대값에 GEV를 직접 적합하는 것보다 안정적입니다.

### 5-4. 부트스트랩 신뢰구간

표본이 10개년뿐이라 P95가 얼마나 흔들리는지 확인했습니다.

```python
boots = [np.percentile(rng.choice(vals, size=10, replace=True), 95)
         for _ in range(10000)]
ci = [np.percentile(boots, 2.5), np.percentile(boots, 97.5)]
```

원 표본에서 **복원추출로 10,000번 재표집**해 각각 P95를 구하고, 그 분포의 2.5~97.5% 구간을 취합니다.
결과: 점추정 2.0일, **95% CI [1.0, 2.0]일**.

### 5-5. Mann-Kendall 추세검정

고립일수 감소 추세가 통계적으로 유의한지 검정합니다. **비모수 검정**이라 정규성 가정이 필요 없어
소표본·이산값에 적합합니다.

```python
S = Σ sign(x[j] - x[i])  for all i<j        # -26
Var(S) = [n(n-1)(2n+5) - 동점보정] / 18
Z = (S+1)/√Var(S)                            # -2.543
p = 2(1 - Φ(|Z|))                            # 0.011
Sen기울기 = median[(x[j]-x[i])/(j-i)]        # -0.33일/년
```

**결과**: p=0.011로 감소 추세가 유의합니다. 그런데 **이걸 기준 완화 근거로 쓰지 않았습니다.**
안전 기준에서 유리한 추세를 근거로 기준을 낮추는 건 위험하기 때문입니다. 제안서에 이 판단을 명시했습니다.

### 5-6. 수단 간 의존구조 검정 (φ계수)

상보성이 우연인지 구조적인지 확인합니다.

```python
both = ((fa==1) & (fb==1)).sum()              # 실제 동시불가일
expected = fa.mean() * fb.mean() * len(df)    # 독립이라면 기대되는 값
chi2, pval, _, _ = stats.chi2_contingency(table)
phi = np.sqrt(chi2 / len(df))
```

| 수단쌍 | 기대 | 관측 | 배수 | φ |
|---|---|---|---|---|
| 선박–헬기 | 0.2일 | 24일 | 107배 | **0.821** |
| 선박–드론 | 0.6일 | 15일 | 23배 | 0.291 |
| 헬기–드론 | 0.9일 | 15일 | 16배 | 0.240 |

선박·헬기는 **강하게 동조**(둘 다 시정 지배), 드론과는 **약하게 동조**(드론만 풍속 지배).
→ **상보성은 우연이 아니라 제약 요인이 다른 데서 오는 구조적 성질**임이 입증됩니다.

---

## 6. 민감도 분석 — `src/sensitivity.py`

"임계값을 자의적으로 정한 것 아니냐"는 공격을 막는 부분입니다.

### 6-1. 임계값 스케일링

```python
def _scale_thresholds(base, wind_factor, vis_factor, precip_factor):
    return {mode: ModeThreshold(
        max_wind_mps = th.max_wind_mps * wind_factor,
        min_visibility_m = th.min_visibility_m * vis_factor,
        ...) for mode, th in base.items()}
```

5개 시나리오(기준 / 보수적 / 완화 / 시정만 강화 / 풍속만 강화)를 돌려 결론이 유지되는지 봅니다.

**핵심 결과**: 풍속 기준을 30% 조여 풍속 영향을 최대로 부각시켜도 **선박 불가의 61.5%는 여전히 시정 기인**.
안전재고는 5개 중 4개에서 3일분 동일.

### 6-2. 지형 대표성 민감도

DEM으로 풍속을 보정하는 대신, **"부대 실제 풍속이 관측소보다 X% 높다면"** 을 추적합니다.

```python
df["wind_mps"] = df["wind_mps"] * (1 + uplift)   # +0%, +10%, +20%, +30%
```

**결과**: +30%에서도 선박·헬기 가용률은 0.2%p 변화, **최장 고립일수 2일 불변**.
= 지형 영향이 있어도 안전재고 기준은 안 바뀝니다.
다만 드론은 97.3%→93.4%로 떨어지므로 "드론 주 운용 부대는 현장 실측 필요"라는 결론이 함께 나옵니다.

> **왜 DEM 보정을 안 했나?** 지형으로 국지풍을 정량 예측하는 건 CFD·수치모델링 영역입니다.
> 검증 없이 "예보 7m/s → 실제 11m/s"라고 제시하면 "그 11은 어떻게 계산했나"는 질문 하나에 무너집니다.
> 보정값을 지어내는 대신 **불확실성의 영향 범위**를 보여주는 쪽이 방어적으로 훨씬 튼튼합니다.

---

## 7. 검증 — `tests/test_pipeline.py`

8개의 자동 테스트로 계산 정합성을 확인합니다.

```bash
pytest tests/ -v    # 8 passed
```

| 테스트 | 검증 내용 |
|---|---|
| `test_daily_operability_binary` | 판정 결과가 0/1만 나오는가 |
| `test_annual_availability_range` | 가용률이 0~1 범위인가 |
| `test_isolation_runs_consistency` | **run-length 합 == 전체 고립일수** (핵심 정합성) |
| `test_limiting_factor_breakdown_shares_bounded` | 원인 비중이 0~1 범위인가 |
| `test_classify_current_status_no_probability_leak` | **상태 라벨에 확률 표현이 섞이지 않는가** |
| 기타 3개 | 데이터 생성, 안전재고 타입, 리포트 스키마 |

다섯 번째 테스트가 특이합니다. "확률을 제시하지 않는다"는 **설계 원칙 자체를 테스트로 강제**한 것입니다.

---

## 8. 재현 방법 (심사위원이 직접 확인하려면)

```bash
# 1. 저장소 클론
git clone https://github.com/<본인계정>/supply-window-analysis.git
cd supply-window-analysis

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 기상청에서 데이터 받아 data/raw/ 에 넣기
#    data.kma.go.kr → 기상관측 → 지상관측자료 → 시간자료
#    지점: 백령도(102), 기간: 2016~2025, 변수: 풍속·시정·강수량

# 4. 실행
python run_analysis.py --dir data/raw --station "백령도"

# 5. 결과 확인
#    outputs/figures/*.png   그래프 7장
#    outputs/analysis_report.json   핵심 수치
```

**원본 CSV는 저장소에 포함하지 않았습니다**(`.gitignore` 처리).
기상청에서 누구나 무료로 받을 수 있는 공개 데이터이므로, 저장소에는 코드만 두고
데이터는 각자 받아서 넣는 구조가 재현성 측면에서 더 깔끔합니다.

---

## 9. 예상 질문 대비

| 질문 | 답변 |
|---|---|
| "임계값은 어디서 가져왔나?" | 일반 운용기준 참조한 예시값. 그래서 민감도 분석으로 강건성을 검증했고, 양방향 조정에도 결론 불변 |
| "예측모델은 왜 없나?" | 과거 보급 실적이 정형 DB로 없어(Cold Start) 검증 불가능한 확률을 제시하는 건 부정직. 대신 학습 데이터 없이도 엄밀한 확률통계 기법 적용 |
| "그냥 조건부 필터링 아닌가?" | 1~2단계는 그렇지만, 3단계에서 복합 포아송-기하 재현기간, 부트스트랩 CI, Mann-Kendall, φ계수 검정을 수행. 수문학 확률강우량 산정과 동일 계열 |
| "3일분 근거는?" | 두 독립 방법이 수렴. ① P95(2일)+마진 1일 ② 20년 재현수준 3일(초과확률 4.7%) |
| "실제 보급 이력과 대조했나?" | 안 했고 한계로 명시. 다만 편향 방향은 특정 가능 — 기상이 허용해도 무산될 순 있지만 반대는 드물어, 본 추정은 위험의 하한. 안전마진 1일이 이를 보정 |
| "관측소가 부대를 대표하나?" | 지형 대표성 민감도로 확인. 풍속 +30% 가정에도 최장 고립일수 불변. 단 드론은 영향받으므로 현장 실측 권장 |
| "데이터 검증은?" | 12월 31일 오판정 버그 발견·수정 사례. 고립사건 22건→12건 정정, 잘못된 "12월 집중" 결론이 "7월 해무철 집중"으로 바뀜 |

---

## 부록: 파일별 역할 요약

| 파일 | 줄 수 | 역할 |
|---|---|---|
| `src/config.py` | 63 | 수단별 임계값, 판정 파라미터 |
| `src/load_data.py` | 229 | CSV 로드·병합·전처리, 합성데이터 생성기 |
| `src/descriptive.py` | 178 | 시간/일 단위 판정, 가용률, run-length |
| `src/diagnostic.py` | 84 | 원인 분해, 계절 집중도 |
| `src/inference.py` | 332 | 확률모형, 재현기간, 부트스트랩, 검정 |
| `src/sensitivity.py` | 125 | 임계값 시나리오, 스윕 |
| `src/visualize.py` | 221 | 그래프 7종 |
| `run_analysis.py` | 140 | 전체 파이프라인 실행 |
| `tests/test_pipeline.py` | 93 | 자동 검증 8종 |
| **합계** | **1,465** | |
