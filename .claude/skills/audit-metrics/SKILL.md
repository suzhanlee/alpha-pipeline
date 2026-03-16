---
name: audit-metrics
description: |
  퀀트 리서치 코드베이스의 금융 성과 지표(Sharpe Ratio, CAGR, Max Drawdown,
  Win Rate, 포트폴리오 집계)가 이론 정의와 일치하는지 검증.
  수식 오류, 연율화 실수, 정밀도 손실, 집계 방법론 불일치를 탐지한다.
  사용 시점: "금융 지표 감사", "Sharpe 공식 검증", "metrics audit",
  "CAGR 계산 확인", "성과 지표 검증"이라고 요청할 때.
---

# Financial Metrics Audit

금융 성과 지표 수식이 이론과 일치하는지 검증합니다.

## Codebase Discovery

점검 전, 다음 grep/glob으로 관련 파일을 찾아 역할을 바인딩하라.

1. **지표 모듈** — `sharpe|cagr|max_drawdown|drawdown|win_rate` (대소문자 무관) 함수/변수명 포함 파일; `sqrt(252)|np.sqrt(252)|\*\*(1\s*/\s*years)` 패턴도 검색
2. **무위험 수익률 설정** — config/settings 파일에서 `RISK_FREE_RATE|risk_free|rf_rate` 추출; 단위(연율/일별) 확인
3. **지표 호출 지점** — `compute_metrics(|calculate_metrics(|get_metrics(` 검색; 인자로 전달되는 `returns`가 포트폴리오 시계열인지 개별 종목 시계열인지 확인
4. **포트폴리오 집계 로직** — `.mean(axis=1)|.sum(axis=1)` + `pd.concat` 패턴; 집계 방식 확인

## 체크리스트

### 1. Sharpe Ratio
- 연간화 계수 `sqrt(252)` 적용 여부 확인
- 올바른 공식: `(excess.mean() / excess.std()) * sqrt(252)`
- Discovery Step 2에서 추출한 risk_free_rate가 연간 기준인데 일간으로 올바르게 환산되는지 (`/252` vs `(1+r)^(1/252)-1`)

### 2. CAGR
- 총 기간 계산: `len(returns) / 252` — 거래일 기준이므로 달력일과 다름, 이 가정이 명시적인지 확인
- 음수 총 수익일 때 `total <= 0` 처리가 정보를 숨기는지 확인

### 3. Max Drawdown
- `(cumulative - rolling_peak) / rolling_peak` — 분모가 0이 되는 케이스 처리 확인
- 결과값 부호 컨벤션 확인 (음수 반환이 맞는지)

### 4. Win Rate
- `returns != 0` 필터링이 의도적인지 확인 (0 수익일을 제외하는 게 맞는 정의인지)

### 5. 수치 정밀도
- `round(..., 4)` 반올림이 downstream 계산에 영향 주는 곳이 있는지 확인

### 6. 포트폴리오 수익 집계 방법
- Discovery Step 3, 4에서 찾은 지표 호출 지점에서 ticker별 수익을 어떻게 포트폴리오 수익으로 합치는지 확인:
  - `mean()` — 동일 가중 평균 (현실적)
  - `sum()` — 단순 합산 (종목 수만큼 레버리지, 비현실적)
  - 가중평균 — 시가총액 또는 사용자 지정 비중 (가장 현실적)
- 집계 방식이 Sharpe/CAGR 수치에 직접 영향을 미치므로 결과 해석 시 반드시 명시

### 7. 지표 적용 수준 명시
- 반환된 지표(Sharpe, CAGR, MDD 등)가 **포트폴리오 전체** 수준인지, **종목 평균** 수준인지 확인
- Discovery Step 3에서 찾은 호출부에 전달되는 `returns` 시리즈가 집계 후 포트폴리오 수익인지, 개별 종목 수익인지 추적
- `num_days` 필드가 전체 백테스트 기간 일수인지, 특정 종목의 거래일 수인지 확인

## 검증 방법

알려진 입력으로 각 함수의 예상 출력을 손으로 계산해서 실제 코드 결과와 비교:
- `returns = pd.Series([0.01] * 252)` → Sharpe, CAGR 예상값 계산
- `returns = pd.Series([-0.5, 0.5])` → MDD 예상값 계산

---

## 출력 형식

아래 형식으로 결과를 작성한 뒤, `reports/audit-metrics.md` 파일로 저장하세요.

---

## audit-metrics 결과 — {오늘 날짜}

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
