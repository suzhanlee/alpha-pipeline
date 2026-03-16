## audit-data 결과 — 2026-03-16

### 요약
| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | 1 |
| 🟠 High | 3 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |

### 발견 항목
| # | 항목 | 파일:라인 | 문제 요약 | 심각도 |
|---|------|----------|----------|--------|
| 1 | Universe `as_of` 파라미터 무시 | `data/universe.py:31` | `as_of` 파라미터를 받지만 항상 `last_date`(마지막 날짜)로 스냅샷을 찍어 실질적으로 미래 정보를 사용한 Look-Ahead Bias 발생 | 🔴 Critical |
| 2 | GAMMA 상장폐지 ticker의 fillna(0) 처리 | `data/loader.py:52`, `runner/backtest.py:72` | GAMMA는 650거래일 이후 데이터가 없음. 포트폴리오 concat 시 `fillna(0)`으로 나머지 ~650일을 0 수익률로 채워 계산 → CAGR, Sharpe, MDD 모두 편향 발생 | 🟠 High |
| 3 | 캐시 무효화 메커니즘 없음 | `data/cache.py:12` | 모듈 레벨 `_cache` dict에 TTL·파일 mtime 체크·크기 제한이 전혀 없음. 소스 CSV 갱신 시 프로세스 재시작 전까지 stale data 반환 | 🟠 High |
| 4 | Sharpe ratio 연환산 누락 | `metrics/performance.py:29` | `excess.mean() / excess.std()`는 일별 Sharpe. `* sqrt(252)` 연환산이 없어 반환값이 연간 기준 대비 약 1/15.87 수준으로 과소 계산됨 | 🟠 High |
| 5 | 전략 인스턴스 캐시의 kwargs 불일치 | `strategy/registry.py:26-28` | `get_strategy(name, **kwargs)` 호출 시 이미 캐시된 인스턴스가 있으면 kwargs를 무시하고 재사용. 다른 파라미터로 동일 전략 호출 시 이전 설정이 그대로 적용됨 | 🟡 Medium |
| 6 | 가격 <= 0 검증 없음 | `data/loader.py:41-61` | `REQUIRED_COLUMNS` 존재 여부만 체크하고 `close <= 0` 행 필터링이 없음. 시뮬레이션 데이터라 현재는 문제없으나, 실제 데이터로 전환 시 `pct_change()` 계산 결과가 오염될 수 있음 | 🟡 Medium |
| 7 | 수정주가(Adjusted Price) | `scripts/generate_data.py:25-50` | 데이터는 `generate_data.py`의 랜덤워크 시뮬레이션으로 생성. 주식 분할·배당 이벤트가 없으므로 수정주가 이슈 **해당 없음** | 🟢 Low |

---

#### 항목별 상세

**#1 — Universe Look-Ahead Bias (Critical)**

`get_universe(df, as_of=None)` 함수는 `as_of` 파라미터를 선언했으나 내부적으로는 항상 `all_dates.max()` (데이터셋 전체의 마지막 날짜)를 기준으로 스냅샷을 반환한다. `backtest.py:51`에서 `as_of` 없이 호출하므로, 백테스트 시작 시점부터 데이터가 존재하는 전 ticker가 아닌 **마지막 날짜에 살아있는 ticker**만 유니버스로 사용된다. GAMMA처럼 중간에 상장폐지된 종목은 유니버스에 포함되지만, 반대로 데이터셋 마지막 날 데이터가 없는 종목은 제외된다. 이는 Survivorship Bias의 변형으로, 시간 축을 따라 유니버스가 변동되는 실제 상황을 반영하지 못한다.

**#2 — 상장폐지 ticker의 0 패딩으로 인한 지표 편향 (High)**

`generate_data.py:63`에서 GAMMA는 650거래일(~2.5년)치 데이터만 생성된다. `backtest.py:72`의 `pd.concat(_ticker_returns, axis=1).fillna(0)`은 GAMMA 데이터가 없는 이후 기간을 0 수익률로 채운다. 이로 인해:
- **Sharpe Ratio**: 0 수익률 날짜가 분자를 줄이고 표준편차를 낮춰 값이 왜곡됨
- **CAGR**: GAMMA의 기여 기간이 절반인데 동등 가중 평균으로 계산되어 후반기 성과를 희석시킴
- **Win Rate**: 0 수익 일수가 `win_rate` 함수(`performance.py:51`)에서 `returns != 0` 필터로 제외되지만, 포트폴리오 평균값에는 이미 반영되어 결과가 혼재됨

올바른 처리: 각 ticker의 유효 거래 기간만 포트폴리오 계산에 포함하거나, 가중치를 date별 활성 ticker 수로 동적 조정해야 한다.

**#3 — 캐시 무효화 없음 (High)**

`data/cache.py`의 `_cache`는 프로세스 생존 기간 동안 영구 보존된다. TTL, 파일 mtime 비교, `maxsize` 제한이 없다. 멀티 worker 환경에서는 각 worker 프로세스가 독립 캐시를 유지하므로 메모리 사용량이 worker 수에 비례해 증가하며, CSV가 갱신되어도 재시작 전까지 이전 데이터가 반환된다.

**#4 — Sharpe Ratio 연환산 누락 (High)**

`performance.py:29`: `return float(excess.mean() / excess.std())`

일별 수익률 기준 Sharpe를 연환산하려면 `* np.sqrt(252)`가 필요하다. 현재 코드는 일별 Sharpe를 그대로 반환하므로, 예를 들어 연환산 Sharpe 1.0인 전략이 약 0.063으로 보고된다. 성과 비교나 임계값 판단 시 심각한 오해를 유발한다.

**#5 — 전략 인스턴스 캐시의 kwargs 무시 (Medium)**

`registry.py:26-28`: 캐시 키가 전략 이름(`name`)만 사용하고 `kwargs`를 포함하지 않는다. `/api/compare` 등으로 같은 전략을 다른 파라미터로 실행할 경우, 두 번째 이후 호출은 첫 번째 인스턴스의 파라미터로 계산된다.

**#6 — 가격 음수/0 검증 없음 (Medium)**

현재 시뮬레이션 데이터에서는 발생하지 않지만, 실제 데이터 전환 시 `close <= 0` 행이 포함되면 `pct_change()` 결과가 음수 무한대 또는 NaN이 되어 이후 모든 수익률 계산이 오염된다. 방어적 검증 코드가 없다.

---

### 종합 판단
**신뢰 가능 여부**: 조건부

**이유**: Universe Look-Ahead Bias(#1)와 Sharpe Ratio 연환산 누락(#4)은 성과 수치를 구조적으로 왜곡하며, 상장폐지 ticker의 0 패딩(#2)은 포트폴리오 지표 전반에 편향을 주입한다. 이 세 항목이 수정되기 전까지는 출력된 성과 수치를 절대값으로 신뢰해서는 안 되며, 전략 간 상대 비교 용도로만 제한적으로 사용 가능하다.
