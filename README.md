# 보급윈도우 (Supply-Window)

> 격오지·도서·GP 다중수단(선박·헬기·드론) 기상 운용가능성 분석 및
> 선제보급 안전재고 산정 파이프라인

**2026년 육군 빅데이터 분석 경연대회 — 정책·아이디어 부문 출품작 분석 코드**

---

## 핵심 설계 원칙 (심사 방어 논리)

이 저장소는 아래 4가지 원칙을 코드 레벨에서 강제합니다.

| 원칙 | 구현 방식 |
|---|---|
| **1. 확률을 만들어내지 않는다** | `prescriptive.classify_current_status()`는 "가능/제한적/불가" 라벨만 반환. `35%` 같은 미검증 확률 표현 없음 |
| **2. DEM으로 풍속을 예측하지 않는다** | `diagnostic.station_topography_note()`에 지형정보는 "위험 특성 표시"에만 쓴다는 원칙을 문서화. 실제 풍속 수치 산출 로직 없음 |
| **3. 예측모델 없이 분석의 실질을 확보한다** | 1~3단계 전부 **기술통계·교차분석·백분위수** 기반. 머신러닝 학습 모델 미사용 (Cold-Start 문제 정면 방어) |
| **4. 최종 결정은 지휘관에게 남긴다** | `prescriptive.supply_window_recommendation()`의 출력은 "권고"이지 "명령"이 아님. 모든 결과에 `비고` 필드로 명시 |

---

## 분석 3단계 구조

```
1단계: 기술통계 (Descriptive)
  "무슨 일이 있었는가" — 재현 가능한 단순 집계
  └─ src/descriptive.py

2단계: 진단적 분석 (Diagnostic)
  "왜 그런 패턴이 나오는가" — 계절성·원인 교차분석
  └─ src/diagnostic.py

3단계: 처방적 로직 (Prescriptive, 예측 아님)
  "그래서 안전재고를 며칠분으로 잡을 것인가" — 백분위수 기반 규칙
  └─ src/prescriptive.py
```

---

## 빠른 시작

```bash
pip install -r requirements.txt

# 합성(가상) 데이터로 전체 파이프라인 데모 실행
python run_analysis.py --demo --station "가상_서해5도_관측소"

# 실제 기상청 CSV로 실행 (아래 "실데이터 연결" 참고)
python run_analysis.py --csv data/raw/실제파일.csv --station "○○부대"

# 연도별 CSV 폴더 + 통계적 추론(4단계)·민감도(5단계)까지 전체 실행
#   → 그래프 05~07 및 추론/민감도 CSV가 추가로 생성됩니다
python run_analysis.py --dir data/raw --station "백령도" --full
```

> `--full` 없이 실행하면 1~3단계와 그래프 4종만 생성됩니다.
> 저장소에 커밋된 `outputs/`는 백령도 실측자료(2016~2025)에 `--full`을 적용한 결과입니다.

실행하면 `outputs/` 아래에 다음이 생성됩니다.

```
outputs/
├── figures/
│   ├── 01_monthly_availability_heatmap.png      월별×수단별 가용률 히트맵
│   ├── 02_annual_isolation_trend.png             연도별 최장 고립일수 추이
│   ├── 03_isolation_calendar_YYYY.png            동시불가 캘린더 히트그리드
│   └── 04_limiting_factor_breakdown.png          수단별 원인 분해
├── daily_operability.csv        일자별 수단별 운용가능 여부 원자료
├── annual_availability.csv      연도별 가용률
├── monthly_availability.csv     월별 가용률
├── limiting_factor_breakdown.csv
├── seasonal_concentration.csv
└── analysis_report.json         제안서에 바로 인용 가능한 핵심 수치 요약
```

---

## 원본 데이터 (저장소에 포함됨)

본 저장소는 분석에 사용한 **기상청 ASOS 원본 CSV를 그대로 포함**합니다.
별도 다운로드 없이 아래 한 줄로 전체 결과를 재현할 수 있습니다.

```bash
python run_analysis.py --dir data/raw --station "백령도" --full
```

| 항목 | 내용 |
|---|---|
| 관측지점 | 백령도 (지점번호 102) |
| 기간 | 2016 ~ 2025 (10년, 연도별 CSV 10개) |
| 항목 | 기온 · 강수량 · 풍속 · 풍향 · 습도 · 시정 |
| 출처 | 기상자료개방포털 [data.kma.go.kr](https://data.kma.go.kr) 공개자료 |
| 인코딩 | CP949 (포털 기본값, 로더가 자동 처리) |

> ⚠ `data/raw/`에는 공개 기상자료만 둡니다.
> 부대 위치·편성·보급 실적 등 비공개 정보는 절대 포함하지 마십시오.

---

## 다른 관측지점으로 교체하는 방법

1. [data.kma.go.kr](https://data.kma.go.kr) 회원가입 → 기상관측 → 지상관측자료 → 시간자료
2. 대상 부대 인근 **ASOS**(종관, 정확도↑) 또는 **AWS**(방재, 지점 밀도↑) 관측지점 선택
3. 최근 **10년치** CSV 다운로드 → `data/raw/`에 저장
4. `src/load_data.py`의 `COLUMN_MAP` 딕셔너리를 다운로드한 CSV의 실제 헤더에 맞게 한 줄만 수정
5. `python run_analysis.py --csv data/raw/파일명.csv --station "부대명"` 실행

> ⚠️ 현재 `--demo` 모드의 수치는 **전부 합성(가상) 데이터**입니다.
> 파이프라인이 정상 동작하는지 검증하기 위한 것이며, 실제 안전재고 산정에는
> 절대 사용하지 마십시오. 실제 CSV로 교체해야 유효한 결과입니다.

---

## 운용 임계값 수정

`src/config.py`의 `THRESHOLDS` 딕셔너리에 현재 예시값이 들어 있습니다.
**실제 제안서 제출 전 반드시 실제 교범·제원표 수치로 교체**하세요.

```python
"드론": ModeThreshold(
    max_wind_mps=8.0,      # ← 실제 기종 한계풍속으로 교체
    max_gust_mps=12.0,
    min_visibility_m=500,
    max_precip_mm_h=3.0,
    source="국방기술품질원 25kg급 국방표준 발췌 필요",  # ← 실제 조항 번호 기입
),
```

---

## 테스트

```bash
pytest tests/ -v
```

8개 테스트가 다음을 검증합니다: 데이터 생성 무결성, 운용가능 판정의 이진성,
가용률의 범위(0~1), 연속고립일 run-length 합산 정합성, 안전재고 값의 타입·양수 여부,
원인분해 비중의 범위, **상태 라벨에 확률 표현이 섞이지 않는지**(설계 원칙 방어),
요약 리포트 스키마.

---

## 프로젝트 구조

```
supply-window-analysis/
├── run_analysis.py          전체 파이프라인 실행 스크립트
├── src/
│   ├── config.py             수단별 운용 임계값 설정
│   ├── load_data.py          기상청 CSV 로더 + 합성데이터 생성기
│   ├── descriptive.py        1단계: 기술통계
│   ├── diagnostic.py         2단계: 진단적 분석
│   ├── prescriptive.py       3단계: 처방적 로직 (안전재고 산정)
│   ├── inference.py          4단계: 통계적 추론 (Markov 지속성, Poisson 빈도,
│   │                                 복합 포아송-기하 재현수준, 부트스트랩 CI,
│   │                                 Mann-Kendall 추세, φ계수 수단독립성 검정)
│   ├── sensitivity.py        5단계: 임계값 민감도 · 시나리오 분석
│   └── visualize.py          그래프 7종 생성
├── tests/
│   └── test_pipeline.py      pytest 유닛테스트 8종
├── ANALYSIS_METHOD.md       분석방법 상세 설명서
├── proposal.md              정책 제안서
├── data/raw/                 (실제 CSV를 여기에 넣으세요 — 원본은 .gitignore 처리)
├── outputs/                  분석 결과 (CSV/JSON/그래프)
└── requirements.txt
```

---

## 다음 단계 (로드맵)

- [ ] 실제 기상청 CSV 연결 및 재실행
- [ ] `config.py` 임계값을 실제 교범값으로 교체
- [ ] 대시보드 UI(웹/모바일) 목업 제작 — 이 분석 결과를 시각화 레이어로 연결
- [ ] 2단계 데이터 축적용 운용 결과 입력 스키마 설계 (시도/성공/회항사유)
- [ ] 3단계 고도화: 운용 데이터 100건 이상 축적 후 확률 예측 모델 검토
