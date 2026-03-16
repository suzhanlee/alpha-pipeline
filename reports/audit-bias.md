## audit-bias 결과 — 2026-03-16

### 요약
| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | 3 |
| 🟠 High | 2 |
| 🟡 Medium | 3 |
| 🟢 Low | 1 |

---

### 발견 항목

| # | 항목 | 파일:라인 | 문제 요약 | 심각도 |
|---|------|----------|----------|--------|
| 1 | SMA Cross 룩어헤드 편향 | `strategy/sma_cross.py:41` | `signal * daily_return` — shift(1) 누락으로 당일 시그널로 당일 수익 계산 | 🔴 Critical |
| 2 | Sharpe Ratio 미연환산 | `metrics/performance.py:29` | `mean/std` 반환 — `* sqrt(252)` 누락으로 일간 Sharpe를 연간으로 보고 | 🔴 Critical |
| 3 | Universe `as_of` 파라미터 무시 | `data/universe.py:28-31` | 파라미터를 받지만 항상 `last_date` 기준으로 평가 — 생존편향 | 🔴 Critical |
| 4 | MACD 생성자 파라미터 오타 | `strategy/macd.py:22` | `signal: int = settings.MACD_SLOW` 는 26을 기본값으로 사용; `MACD_SIGNAL`(9)이어야 함 | 🟠 High |
| 5 | lookahead 테스트가 실제로 편향을 잡지 못함 | `tests/test_signals.py:56-64` | `test_no_lookahead`의 허용 임계값이 `> -5.0`으로 과도하게 느슨하여 lookahead bias 여부와 무관하게 통과 | 🟠 High |
| 6 | Train/Test 분리 없음 (In-Sample 성과) | `runner/backtest.py` 전체 | 전체 데이터를 단일 기간으로 백테스트 — walk-forward/hold-out 구간 없음 | 🟡 Medium |
| 7 | 다중 전략 비교 시 다중검정 조정 없음 | `runner/dispatcher.py:27-34` | 3개 전략 병렬 실행 후 best-pick, p-value 보정(Bonferroni 등) 없음 | 🟡 Medium |
| 8 | SMA 거래비용 계산 타이밍 불일치 | `strategy/sma_cross.py:38-41` | turnover는 당일 시그널 기준으로 계산되나, strategy_return에 shift(1) 없이 비용 차감 — 비용 적용 시점 모호 | 🟡 Medium |
| 9 | 합성 데이터 사용 (실데이터 아님) | `scripts/generate_data.py` 전체 | 모든 성과 지표는 Gaussian random walk 기반 합성 데이터에서 도출 — 실제 시장 마찰 없음 | 🟢 Low |

---

### 상세 설명

#### #1 — SMA Cross 룩어헤드 편향 (Critical)

`strategy/sma_cross.py` line 41:
```python
df["strategy_return"] = df["signal"] * df["daily_return"] - cost_per_day
```
`signal`에 `.shift(1)`이 없으므로, 오늘 종가로 계산된 SMA 시그널을 오늘의 수익에 그대로 곱한다.
실제로는 오늘 종가를 보고 내일 포지션을 잡을 수 있으므로, 올바른 패턴은
`df["signal"].shift(1) * df["daily_return"]`이다.

MACD(`macd.py:45`)와 RSI(`rsi.py:62`)는 `shift(1)`을 올바르게 적용하고 있어 대조적이다.
이 편향은 SMA Cross 전략의 Sharpe, CAGR, 승률을 실질보다 과장한다.

#### #2 — Sharpe Ratio 미연환산 (Critical)

`metrics/performance.py` line 29:
```python
return float(excess.mean() / excess.std())
```
일간 excess return의 mean/std를 그대로 반환하며 `* np.sqrt(252)`가 없다.
`volatility_annual`(line 65)은 `std * sqrt(252)`로 올바르게 연환산하지만,
Sharpe는 일간 값(≈ 연간 Sharpe / 15.87)을 반환하므로 수치가 극히 작게 보고된다.

`test_metrics.py:32`의 `test_sharpe_annualised` 테스트는 이 버그를 명시적으로 탐지하도록
설계되어 있으며, 실행하면 실패해야 한다. 즉, 이 버그는 테스트에 이미 문서화되었으나
수정되지 않은 상태이다.

#### #3 — Universe `as_of` 파라미터 무시 (Critical)

`data/universe.py` line 17에서 `as_of` 파라미터를 선언하나, 실제 코드(line 28-31)는
이를 전혀 사용하지 않고 항상 전체 데이터의 `last_date`로 스냅샷을 취한다:
```python
last_date = all_dates.max()   # as_of 무시
snapshot = df.loc[last_date]
```
결과적으로 `runner/backtest.py:51`의 `get_universe(df)` 호출은 데이터 종료 시점
기준의 생존 종목만 반환한다. GAMMA처럼 중도 상장폐지된 종목은 백테스트 전 기간에 걸쳐
유니버스에서 제외되어 생존편향이 발생한다.

`test_backtest.py:55`의 `test_universe_excludes_delisted` 테스트는 이 문제를 정확히
탐지하도록 설계되었고, 실행 시 실패한다(GAMMA가 early_date에도 유니버스에 없으므로).

#### #4 — MACD 생성자 파라미터 오타 (High)

`strategy/macd.py` line 22:
```python
def __init__(self, fast=12, slow=26, signal: int = settings.MACD_SLOW):
```
`signal` 파라미터의 기본값이 `settings.MACD_SLOW`(=26)로 잘못 참조되어 있다.
의도는 `settings.MACD_SIGNAL`(=9)이어야 한다.
현재 기본 설정으로 실행하면 signal 기간이 26이 되어 MACD 특성이 완전히 달라진다.

#### #5 — lookahead 테스트 실효성 없음 (High)

`tests/test_signals.py:63-64`:
```python
# This passes regardless of look-ahead bias — threshold is too weak
assert sharpe > -5.0, "Sharpe is extremely negative — strategy is broken"
```
테스트 코드 자체에 "threshold is intentionally too loose, so look-ahead bias can still
pass this test"라고 명시되어 있다. #1의 SMA lookahead 버그가 존재해도 이 테스트는
통과하므로 CI에서 편향을 잡지 못한다.

올바른 lookahead 탐지 방법: 완전 랜덤(pure-noise) 가격 시계열에서 실행한 전략의
Sharpe가 `|Sharpe| < 1.0` 범위 안에 있어야 한다. MACD 테스트(`test_signals.py:88-115`)는
이 방식을 올바르게 구현한 참고 예시이다.

#### #6 — In-Sample 성과 보고 (Medium)

백테스트 러너(`runner/backtest.py`)는 전체 데이터(~5년)를 단일 기간으로 사용하며
학습 구간 / 검증 구간 분리, walk-forward validation, 또는 expanding window 분할이
존재하지 않는다. 파라미터(SMA window, MACD fast/slow/signal, RSI 기간/임계값)는
`config.py`에 하드코딩되어 있으나, 이 기본값들이 동일 데이터를 사전에 보고 선택된
것인지 확인할 수 없다.

보고된 모든 Sharpe/CAGR/MDD 수치는 **in-sample 성과**이며, 미래 데이터에 대한
예측력을 보장하지 않는다.

#### #7 — 다중 전략 비교 시 다중검정 조정 없음 (Medium)

`runner/dispatcher.py`는 SMA Cross, MACD, RSI를 병렬 실행하고 결과를 나란히 반환한다.
3개 전략 중 best-pick 시, 5% 유의수준 기준의 실제 유형 I 오류율은 최대
1 - (1-0.05)^3 ≈ 14%로 증가한다. 파라미터 변형을 포함하면 실질적 검정 횟수는
더욱 늘어난다.

비교 결과 보고 시 "다중 비교 조정 없이 선택된 best-pick"임을 명시해야 하며,
필요 시 Bonferroni 보정 또는 White's Reality Check 적용을 권고한다.

#### #8 — SMA 비용 계산 타이밍 불일치 (Medium)

`sma_cross.py`에서 `turnover`는 당일 `signal`의 변화로 계산되나,
`strategy_return` 자체가 shift(1)이 없으므로 비용과 수익이 동일한 당일에 함께
계산된다. #1이 수정되어 `shift(1)`이 추가되면, turnover도 `shift(1)` 이후의 신호
변화를 기준으로 재산정해야 비용 적용 날짜가 정합성을 갖는다.

#### #9 — 합성 데이터 (Low)

`scripts/generate_data.py`는 Gaussian random walk(GBM 근사) 기반으로 가격 데이터를
생성한다. 팻테일(fat-tail), 변동성 군집(volatility clustering), 시장 충격(market impact),
유동성 제한 등 실제 시장 특성이 반영되지 않아, 측정된 성과 지표가 실거래 환경에서
재현될 가능성은 낮다. 내부 연구 목적임을 감안하면 허용 가능한 수준이나,
결과 해석 시 명시적으로 언급해야 한다.

---

### 종합 판단

**신뢰 가능 여부**: No

**이유**: SMA Cross 전략에 룩어헤드 편향(shift 누락)이 있어 성과가 과장되며,
Sharpe Ratio가 연환산되지 않아 보고 수치 자체가 잘못되었고, Universe 필터가 생존편향을
교정하지 못한다 — 세 가지 Critical 결함이 동시에 존재하므로 현재 상태의 백테스트
결과는 신뢰할 수 없다.
