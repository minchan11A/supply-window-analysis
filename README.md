# 보급윈도우 (Supply-Window)

도서·격오지 부대의 기상 조건을 분석해 **보급 수단별 운용 가능일을 집계하고,
안전재고를 며칠분으로 잡아야 하는지 산정**하는 분석 파이프라인입니다.

기상청 관측자료(풍속·시정·강수)를 수단별 운용 한계기준과 대조해
선박·헬기·드론 각각이 며칠이나 뜰 수 있었는지, 세 수단이 **동시에 막힌 날**이
얼마나 이어졌는지를 계산합니다.

---

## 무엇을 계산하는가

```
기상 관측자료 (시간 단위)
        │
        ├─ 수단별 한계기준과 대조 ─────→ 시간별 운용가능 여부
        │                                      │
        │                              하루 중 연속 6시간 이상 가능?
        │                                      ↓
        │                                 일별 운용가능일
        │                                      │
        ├─ 세 수단 모두 불가한 날 = 고립일 ────┤
        │                                      ↓
        └─ 연속 고립일수의 95백분위 + 여유 1일 → 권고 안전재고 일수
```

핵심 산출물은 **권고 안전재고 일수** 하나입니다. 나머지 분석은 그 숫자가
어떤 근거에서 나왔고, 가정을 바꿔도 견디는지를 뒷받침합니다.

| 단계 | 파일 | 답하는 질문 |
|---|---|---|
| 1. 기술통계 | `src/descriptive.py` | 수단별로 며칠이나 운용 가능했는가 |
| 2. 진단 | `src/diagnostic.py` | 못 뜬 이유는 풍속인가 시정인가, 계절성은 있는가 |
| 3. 처방 | `src/prescriptive.py` | 안전재고를 며칠분으로 잡을 것인가 |
| 4. 추론 | `src/inference.py` | 그 숫자가 통계적으로 뒷받침되는가 (신뢰구간 포함) |
| 5. 민감도 | `src/sensitivity.py` | 기준값을 바꿔도 결론이 유지되는가 |

---

## 실행

```bash
pip install -r requirements.txt
python run_analysis.py --dir data/raw --station "백령도" --full
```

원본 데이터가 저장소에 포함돼 있어 **별도 다운로드 없이 위 한 줄로
`outputs/`의 모든 결과가 그대로 재현**됩니다.

`--full`을 빼면 1~3단계와 그래프 4종만 생성되고 4~5단계는 건너뜁니다.

### 제안서 docx 생성 (선택)

`outputs/figures/`의 그래프를 삽입한 제안서 Word 파일을 만듭니다.

```bash
npm install
npm run build:proposal    # → outputs/보급윈도우_제안서(공모서식).docx
```

분석 파이프라인과는 독립적이며, 분석 결과를 쓰지 않는다면 실행할 필요가 없습니다.

### 산출물

```
outputs/
├── figures/
│   ├── 01_monthly_availability_heatmap.png   월별×수단별 가용률
│   ├── 02_annual_isolation_trend.png         연도별 최장 고립일수
│   ├── 03_isolation_calendar_YYYY.png        고립일 캘린더 (최악·최근 연도)
│   ├── 04_limiting_factor_breakdown.png      불가 원인 분해 (풍속/시정/강수)
│   ├── 05_sensitivity_analysis.png           기준값 변경 시나리오
│   ├── 06_return_level.png                   재현기간별 고립 수준
│   ├── 07_terrain_sensitivity.png            관측소-부대 간 풍속 차이 가정
│   └── 08_marginal_contribution.png          수단별 한계 보완 효과
├── analysis_report.json      핵심 수치 요약 (권고 안전재고 · 산정근거)
├── daily_operability.csv     일자별 수단별 운용가능 여부 (원자료)
├── annual_availability.csv   연도별 가용률
├── monthly_availability.csv  월별 가용률
├── limiting_factor_breakdown.csv
├── seasonal_concentration.csv
├── mode_dependence.csv       수단 간 독립성 검정 (φ계수)
├── sensitivity_scenarios.csv
├── terrain_representativeness.csv
└── threshold_sweep_ship.csv
```

---

## 부대 정보를 어디에 넣는가

이 저장소는 **공개 기상자료와 예시 임계값만으로** 동작합니다.
실제 부대에 적용하려면 아래 네 곳을 채웁니다.

### 1. 운용 한계기준 — `src/config.py`

가장 중요한 입력입니다. 현재는 **전부 예시값**이며, 실제 기종의
운용교범·제원표 수치로 교체해야 결과가 유효합니다.

```python
"드론": ModeThreshold(
    max_wind_mps=8.0,        # 한계 평균풍속
    max_gust_mps=12.0,       # 한계 순간최대풍속
    min_visibility_m=500,    # 최소 시정
    max_precip_mm_h=3.0,     # 최대 시간강수량
    source="",               # 근거 조항 번호
),
```

같은 파일의 아래 상수도 부대 실정에 맞춰 조정합니다.

| 상수 | 의미 | 기본값 |
|---|---|---|
| `MIN_OPERATIONAL_WINDOW_HOURS` | 하루를 '운용가능일'로 인정할 최소 연속 가능시간 | 6시간 |
| `SAFETY_STOCK_PERCENTILE` | 안전재고 산정 기준 백분위수 | 95 |
| `MIN_ISOLATION_EVENT_DAYS` | '연속 고립 사건'으로 집계할 최소 일수 | 3일 |

### 2. 관측자료 — `data/raw/`

대상 부대 인근 관측지점의 시간자료 CSV를 넣습니다.
[기상자료개방포털](https://data.kma.go.kr) → 기상관측 → 지상관측자료 → 시간자료
에서 최근 10년치를 받습니다. 지점은 **ASOS**(정확도 우선) 또는
**AWS**(지점 밀도 우선) 중 부대에 더 가까운 쪽을 택합니다.

헤더가 다르면 `src/load_data.py`의 `COLUMN_MAP` 한 줄만 수정하면 됩니다.

### 3. 부대명 — 실행 인자

```bash
python run_analysis.py --dir data/raw --station "○○부대" --full
```

그래프 제목과 리포트 표기에만 쓰입니다.

### 4. 현재 재고·운용 상태 — `run_analysis.py`

실시간 판정(`supply_window_recommendation`)에 넘기는 예시 시나리오가
`run_analysis.py`에 하드코딩돼 있습니다. 실제 운용에 연결할 때는
현재 재고 일수와 수단별 상태를 이 자리에 연결합니다.

---

## 보안 주의

> **`data/raw/`에는 공개 기상자료만 둡니다.**
> 부대 위치·편성·보급 실적 등 비공개 정보는 절대 포함하지 마십시오.

`src/config.py`의 임계값을 **실제 교범 수치로 교체하는 순간**, 이 저장소는
장비 운용 한계가 담긴 자료가 됩니다. 공개 저장소에 그대로 두지 말고
비공개로 전환하거나 해당 파일을 분리해 관리하십시오.

---

## 설계상 하지 않는 것

결과를 읽을 때 오해가 없도록, 이 파이프라인이 **의도적으로 산출하지 않는**
것을 밝혀둡니다.

- **확률을 만들어내지 않습니다.** 상태는 "가능/제한적/불가" 라벨로만 반환하며,
  `35%` 같은 미검증 확률값을 생성하지 않습니다.
- **지형으로 풍속을 예측하지 않습니다.** 관측·예보값을 그대로 쓰고, 지형은
  주의 플래그로만 다룹니다. 관측소와 부대의 풍속 차이는 예측 대신
  `07_terrain_sensitivity.png`에서 **가정별 민감도**로 제시합니다.
- **학습 모델을 쓰지 않습니다.** 전 단계가 집계·교차분석·백분위수 기반이라
  운용 데이터 축적 없이도 즉시 동작합니다.
- **결정하지 않습니다.** 출력은 권고이며, 최종 판단은 지휘관 몫입니다.

---

## 테스트

```bash
pytest tests/ -v
```

데이터 무결성, 운용가능 판정의 이진성, 가용률 범위(0~1), 연속고립일 합산
정합성, 안전재고 값의 타입·부호, 원인분해 비중 범위, 상태 라벨에 확률 표현이
섞이지 않는지, 요약 리포트 스키마 — 8개 항목을 검증합니다.

---

## 구조

```
supply-window-analysis/
├── run_analysis.py        전체 실행 스크립트
├── proposal_build_docx.js 제안서 docx 생성 (Node, 선택)
├── src/
│   ├── config.py           운용 한계기준 · 산정 상수  ← 부대별 수정 지점
│   ├── load_data.py        기상청 CSV 로더
│   ├── descriptive.py      1단계: 기술통계
│   ├── diagnostic.py       2단계: 진단
│   ├── prescriptive.py     3단계: 안전재고 산정
│   ├── inference.py        4단계: 통계적 추론
│   ├── sensitivity.py      5단계: 민감도 분석
│   └── visualize.py        그래프 생성
├── data/raw/              기상청 원본 CSV (백령도 2016~2025 포함)
├── outputs/               분석 결과
├── tests/                 pytest 8종
├── ANALYSIS_METHOD.md     분석방법 상세 설명
└── proposal.md            정책 제안서
```

### 포함된 데이터

| 항목 | 내용 |
|---|---|
| 관측지점 | 백령도 (지점번호 102) |
| 기간 | 2016 ~ 2025 (10년) |
| 항목 | 기온 · 강수량 · 풍속 · 풍향 · 습도 · 시정 |
| 출처 | 기상자료개방포털 공개자료 |
| 인코딩 | CP949 (로더가 자동 처리) |
