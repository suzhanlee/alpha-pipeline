## audit-metrics 결과 — 2026-03-16

### 요약
| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | 1 |
| 🟠 High | 0 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |

### 발견 항목
| # | 항목 | 파일:라인 | 문제 요약 | 심각도 |
|---|------|----------|----------|--------|
| 1 | Sharpe Ratio — 연간화 계수 누락 | `metrics/performance.py:29` | `sqrt(252)` 미적용으로 Sharpe가 실제값의 약 1/16 수준으로 반환됨 | 🔴 Critical |
| 2 | CAGR — 음수 총수익 처리 | `metrics/performance.py:44` | `total <= 0`일 때 0.0 반환으로 손실 정보가 은폐됨 | 🟡 Medium |
| 3 | Win Rate — 0 수익일 제외 처리 | `metrics/performance.py:51` | `returns != 0` 필터로 포지션 없는 날을 분모에서 제외하며, 이 정의가 문서화되지 않음 | 🟡 Medium |
| 4 | risk_free_rate 일별 환산 방식 | `metrics/performance.py:23` | 단순 나눗셈(`/ 252`) 사용; 이론적으로 정확한 `(1+r)^(1/252)-1` 대비 오차가 있으나 실용 범위 내 수준 | 🟢 Low |

---

#### 항목 1 상세 — Sharpe Ratio 연간화 계수 누락 (Critical)

**현재 코드 (`metrics/performance.py:29`)**
```python
return float(excess.mean() / excess.std())
```

**올바른 공식**
```python
return float((excess.mean() / excess.std()) * np.sqrt(252))
```

**수치 검증**

`returns = pd.Series([0.001] * 252 + noise)` (mean ≈ 0.001, std ≈ 0.01, rf = 0.0) 가정 시:
- 일간 Sharpe = 0.001 / 0.01 = **0.1**
- 연간 Sharpe = 0.1 × √252 ≈ **1.587**
- 현재 코드 반환값: **0.1** (연간화 없음)

`test_metrics.py:32`의 `assert sharpe > 1.0` 테스트가 이 버그를 감지하도록 설계되어 있으나, 해당 테스트는 현재 **실패** 상태임을 의미한다. Sharpe 값이 실제보다 약 15.87배 낮게 출력되어, 전략 성과 비교 및 투자 판단에 직접적인 오류를 초래한다.

---

#### 항목 2 상세 — CAGR 음수 총수익 처리 (Medium)

**현재 코드 (`metrics/performance.py:44`)**
```python
if years == 0 or total <= 0:
    return 0.0
```

`total <= 0`(총 누적 수익이 음수 또는 0)인 경우 CAGR을 0.0으로 반환하면, 실제로 큰 손실이 발생한 전략도 CAGR = 0으로 표시된다. 음수 CAGR은 수학적으로 실수 범위에서 정의되지 않으므로 `float('nan')` 또는 별도 오류 코드를 반환하는 것이 정보 손실을 방지한다.

---

#### 항목 3 상세 — Win Rate 0 수익일 제외 (Medium)

**현재 코드 (`metrics/performance.py:51`)**
```python
active = returns[returns != 0]
```

포지션이 없거나 신호가 0인 날(strategy_return = 0)을 분모에서 제외한다. 이는 "실제 거래가 발생한 날 기준 승률"이라는 특수한 정의이며, 일반적인 Win Rate(전체 기간 기준)와 다르다. 이 정의가 문서에 명시되지 않으면 사용자가 수치를 오해할 수 있다.

---

#### 항목 4 상세 — risk_free_rate 일별 환산 (Low)

**현재 코드 (`metrics/performance.py:23`)**
```python
daily_rf = risk_free_rate / 252
```

이론적으로 정확한 환산은 `(1 + risk_free_rate) ** (1/252) - 1`이다. rf = 4% 기준:
- 단순 나눗셈: 0.04 / 252 = **0.0001587**
- 복리 환산: (1.04)^(1/252) - 1 = **0.0001549**

오차는 약 0.4bp/day로, 연간 Sharpe 수준에서는 무시 가능한 범위이나 이론적 정확성 측면에서 기록한다.

---

#### 포트폴리오 집계 방식 확인

**`runner/backtest.py:72`**
```python
portfolio = pd.concat(_ticker_returns, axis=1).fillna(0).mean(axis=1).dropna()
```

동일 가중(equal-weight) 평균을 사용한다. 이는 현실적인 방식이며, `sum()` 집계(레버리지 효과)가 아니다. 반환된 Sharpe, CAGR, MDD 등 모든 지표는 **포트폴리오 전체 수준**의 지표이다.

- `fillna(0)`: 특정 종목의 거래 없는 날을 0 수익으로 처리 — 동일 가중 분모 보정 없이 단순 0 채움으로, 종목 수가 다른 구간에서 평균이 희석될 수 있다.
- `num_days`: 집계 후 포트폴리오 시계열의 길이이므로 전체 백테스트 기간의 거래일 수를 나타낸다.

---

### 종합 판단
**신뢰 가능 여부**: No

**이유**: `sharpe_ratio()` 함수에서 연간화 계수 `sqrt(252)`가 누락되어 모든 Sharpe 수치가 실제값의 약 1/16 수준으로 반환된다. 이는 전략 성과 비교 결과를 직접적으로 왜곡하므로, 해당 버그 수정 전까지 Sharpe 기반 판단은 신뢰할 수 없다.
