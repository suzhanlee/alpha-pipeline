---
name: audit-bias
description: |
  퀀트 트레이딩 또는 ML 백테스트 코드베이스에서 성과를 과장하는 편향을 탐지.
  Lookahead Bias, Survivorship Bias, Transaction Cost 누락, Overfitting,
  Multiple Testing Bias를 동적 파일 탐색 기반으로 점검한다.
  사용 시점: "백테스트 편향 감사", "lookahead bias 확인", "survivorship bias 검사",
  "bias audit", "백테스트 신뢰성 점검", "편향 점검해줘"라고 요청할 때.
---

# Backtest Bias Audit

백테스트 결과를 실제보다 과장하는 편향을 탐지합니다:
- **Lookahead Bias**: 미래 정보를 시그널 생성에 사용
- **Survivorship Bias**: 살아남은 종목만 유니버스에 포함

## Codebase Discovery

점검 전, 다음 grep/glob으로 관련 파일을 찾아 역할을 바인딩하라.

1. **전략 파일** — `def compute` 또는 `class \w+\(.*[Ss]trategy\)`를 포함하는 .py 파일
2. **신호-수익 연산 라인** — 전략 파일에서 `signal.*return|return.*signal` 패턴 검색
3. **유니버스 함수** — `def get_universe|def eligible_tickers|def tradeable` 포함 파일; 함수 시그니처에 `as_of` 파라미터 유무 확인
4. **백테스트 러너** — `compute_metrics(`와 전략 `compute(`를 모두 호출하는 파일
5. **다중 전략 비교 진입점** — `for strategy in|strategies = \[|asyncio.gather` 패턴; 또는 복수 전략 HTTP 엔드포인트
6. **테스트 파일** — `tests/**/*.py` glob; 내부에서 `lookahead|shift|no_lookahead` 검색

---

## Part 1 — Lookahead Bias

### 1. 시그널 → 수익 적용 시점 (전략별)
위에서 찾은 각 전략 파일의 `compute()` 메서드에서 `strategy_return` 계산 패턴 확인:
- 올바른 패턴: `signal.shift(1) * daily_return` (전날 시그널로 오늘 수익 계산)
- 버그 패턴: `signal * daily_return` (당일 시그널로 당일 수익 = 미래 참조)
- 발견된 각 전략 파일별로 명시적으로 OK / BUG 판정

### 2. 지표 계산의 min_periods
- `rolling()`, `ewm()` 에서 `min_periods` 설정이 없으면 초기 NaN이 암묵적으로 처리될 수 있음
- 발견된 전략 파일 각각의 rolling window 초기화 구간이 시그널에 포함되는지 확인

### 3. 테스트가 lookahead를 실제로 잡는가
- Discovery Step 6에서 찾은 테스트 파일의 lookahead 관련 테스트 확인:
  - 테스트 자체에 "threshold is intentionally too loose" 류의 주석이 있는지
  - 실제로 lookahead bias가 있어도 테스트가 통과하는지 분석
- 올바른 lookahead 탐지 테스트 설계 방향 제시 (pure-noise 데이터에서 Sharpe ≈ 0 이어야 함)

---

## Part 2 — Survivorship Bias

### 1. Universe 필터링 기준
- Discovery Step 3에서 찾은 유니버스 함수 구현 확인:
  - `as_of` 날짜 파라미터를 지원하는지
  - 전체 데이터 기준 현존 ticker만 반환하면 생존편향 있음
  - 올바른 구현: 각 날짜 기준으로 그 시점에 거래 가능했던 ticker 반환

### 2. 상장폐지 ticker 처리
- Discovery Step 6에서 찾은 테스트 파일의 fixture 확인: 상장폐지 시뮬레이션 데이터가 있는지
- universe 테스트가 `as_of` 파라미터를 사용하는지, 실제 구현이 이를 지원하는지 확인

### 3. 백테스트 실행 시점 universe
- Discovery Step 4에서 찾은 백테스트 러너의 universe 호출 방식 확인:
  - 전체 기간 데이터에서 한 번에 universe를 구성하는가 (미래 정보 사용)
  - 올바른 구현: 날짜별 point-in-time universe 사용

### 4. 추가 편향
- **선택편향**: 최소 데이터 일수 필터가 있으면 이미 생존한 종목만 포함
- **데이터 스누핑**: 데이터 생성 스크립트가 있으면 확인 — 시뮬레이션 데이터인지, 실제 데이터 기반인지

---

## Part 3 — Transaction Cost Bias

### 1. 수수료·슬리피지 차감 여부
- 발견된 각 전략 파일의 `strategy_return`이 수수료·슬리피지를 전혀 차감하지 않는지 확인
- Discovery Step 4의 백테스트 러너에서 `compute_metrics()` 호출 시 비용 파라미터가 없으면 gross return 기준임을 명시

### 2. Turnover 계산 및 활용 여부
- `turnover` 컬럼이 전략 DataFrame에 실제로 계산되는지 확인
- turnover가 계산되더라도 비용 추정에 사용되는지, 또는 단순 참고용에 그치는지 확인

### 3. 연간 비용 과장 추정
- 일별 turnover × 편도 수수료(예: 0.05%) × 2 × 252 = 연간 비용 추정
- 고빈도 전략에서 turnover가 높을수록 실제 성과와의 괴리 커짐
- 보고된 Sharpe/CAGR이 비용 차감 후에도 양수인지 개략적으로 평가

---

## Part 4 — Overfitting / In-Sample Bias

### 1. 파라미터 선택 방식
- 발견된 전략 파일의 파라미터(window 크기, period 등)가 전체 데이터를 보고 선택됐는지 확인
- config 파일 또는 전략 기본값이 고정 하드코딩인지, 외부 최적화 결과인지 확인

### 2. Train/Test 또는 Walk-Forward Split 존재 여부
- Discovery Step 4의 백테스트 러너에서 학습 구간 / 검증 구간 분리 로직 확인
- walk-forward validation, anchored split, expanding window 등 시계열 분할 여부 확인

### 3. In-Sample 성과임을 명시
- 위 분리가 없다면 보고된 Sharpe/CAGR/MDD는 **in-sample 성과**임을 결과 섹션에 명시
- 파라미터 최적화 없이 기본값을 사용한 경우에도 데이터 전체를 참고한 것이면 해당

---

## Part 5 — Multiple Testing Bias

### 1. 다중 전략 비교 시 발생 경위
- Discovery Step 5에서 찾은 다중 전략 비교 진입점 확인
- 여러 전략을 병렬 실행하는 방식 확인

### 2. False Discovery 위험
- 다중 전략 비교 시 p-value 조정(Bonferroni, Benjamini-Hochberg 등) 없이 best-pick하면
  우연히 좋아 보이는 전략을 실제 우수한 전략으로 오인할 가능성 있음
- 전략 수가 적어도 파라미터 그리드 탐색을 합산하면 실질적 다중 검정 횟수가 증가함

### 3. 권고 사항
- 비교 결과 보고 시 "이 성과는 다중 비교 조정 없이 선택된 best-pick" 임을 명시
- 실무에서는 hold-out 기간 검증 또는 White's Reality Check 등 통계 보정 필요

---

## 출력 형식

아래 형식으로 결과를 작성한 뒤, `reports/audit-bias.md` 파일로 저장하세요.

---

## audit-bias 결과 — {오늘 날짜}

### 요약
| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | N |
| 🟠 High | N |
| 🟡 Medium | N |
| 🟢 Low | N |

### 발견 항목
| # | 항목 | 파일:라인 | 문제 요약 | 심각도 |
|---|------|----------|----------|--------|
| 1 | (항목명) | (파일:라인) | (한 줄 요약) | 🔴 Critical |

> 문제가 없는 항목은 표에서 생략하고, 각 행 아래 필요 시 들여쓰기로 상세 설명 추가.

### 종합 판단
**신뢰 가능 여부**: Yes / No / 조건부
**이유**: (핵심 근거 1~2문장)
