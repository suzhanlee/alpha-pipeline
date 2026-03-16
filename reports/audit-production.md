## audit-production 결과 — 2026-03-16

### 요약
| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | 4 |
| 🟠 High | 5 |
| 🟡 Medium | 4 |
| 🟢 Low | 3 |

---

### 발견 항목

| # | 항목 | 파일:라인 | 문제 요약 | 심각도 |
|---|------|----------|----------|--------|
| 1 | SMA lookahead bias | `strategy/sma_cross.py:35,41` | signal을 shift 없이 당일 return에 곱해 lookahead bias 발생 | 🔴 Critical |
| 2 | 전략 인스턴스 캐시 — kwargs 무시 | `strategy/registry.py:26-28` | 동일 전략명이 캐시에 있으면 신규 kwargs 무시, 파라미터 변경이 결과에 반영 안 됨 | 🔴 Critical |
| 3 | Survivorship bias — 유니버스 | `data/universe.py:28,31` | `as_of` 파라미터를 받지만 항상 `last_date` 기준으로 universe를 구성해 상장폐지 종목 제외 | 🔴 Critical |
| 4 | Sharpe ratio 미연산화 | `metrics/performance.py:29` | `excess.mean() / excess.std()` — `sqrt(252)` 곱 없음, 연환산 Sharpe가 실제의 1/15.87 수준으로 과소 보고 | 🔴 Critical |
| 5 | MACD signal 기본값 버그 | `strategy/macd.py:22` | `signal: int = settings.MACD_SLOW` — `MACD_SIGNAL(9)` 이 아닌 `MACD_SLOW(26)` 을 기본값으로 사용 | 🟠 High |
| 6 | `/api/backtest` — macd·rsi kwargs 누락 | `main.py:88-91` | `strategy == "sma_cross"` 일 때만 kwargs 구성, macd·rsi는 항상 `{}` 로 전달되어 파라미터 설정이 silent failure | 🟠 High |
| 7 | `/api/compare` — 동일 kwargs 전 전략에 적용 | `main.py:124-125` | `short_window`/`long_window` 를 macd·rsi에도 그대로 전달, 각 전략이 다른 파라미터 이름을 기대함 | 🟠 High |
| 8 | Worker restart 정책 없음 | `docker-compose.yml:32` | `restart: "no"` — 워커 크래시 시 자동 재시작 안 됨, 큐에 적재된 작업이 처리되지 않음 | 🟠 High |
| 9 | `emit()` 미awaited 호출 | `runner/backtest.py:77` | `emit(run_id, "complete", 100)` — `await` 없이 호출, coroutine 객체가 실행되지 않아 완료 이벤트가 SSE로 전달 안 됨 | 🟠 High |
| 10 | 전역 변수 `_ticker_returns` 동시성 버그 | `runner/backtest.py:23,43,56` | 모듈 수준 전역 리스트 사용; `/api/compare`에서 여러 backtest가 동시에 실행되면 리스트가 교차 오염 | 🟡 Medium |
| 11 | SSE `_cursor` 전역 변수 경쟁 조건 | `runner/progress.py:19,27,42` | 단일 전역 `_cursor` 를 모든 run_id가 공유, 동시 실행 중 다른 run의 이벤트가 잘못된 SSE 스트림으로 전달 | 🟡 Medium |
| 12 | Redis 메모리 제한 없음 | `docker-compose.yml:3-11` | Redis 컨테이너에 `mem_limit` 미설정, 결과/큐 누적 시 OOM으로 호스트 메모리 고갈 가능 | 🟡 Medium |
| 13 | 인증/인가 없음 | `main.py:67-125` | 모든 엔드포인트에 인증 미적용; 내부 연구 시스템이라도 네트워크 접근 제어 없을 경우 무제한 접근 가능 | 🟡 Medium |
| 14 | lookahead bias 테스트 미흡 | `tests/test_signals.py:45-64` | `test_no_lookahead` 주석에 "threshold is intentionally too loose" 명시, 실제 lookahead bias를 잡지 못함 | 🟢 Low |
| 15 | `.env.example` 항목 불완전 | `.env.example:1-7` | `REDIS_URL` 등 인프라 관련 환경변수가 `.env.example`에 누락 | 🟢 Low |
| 16 | API·Worker healthcheck 부재 | `docker-compose.yml:13-35` | `api`·`worker` 서비스에 healthcheck 미설정; redis만 healthcheck 있음. `depends_on`이 서비스 준비 여부를 보장 못함 | 🟢 Low |

---

### 상세 설명

**#1 — SMA lookahead bias (`strategy/sma_cross.py:35,41`)**

```python
df["signal"] = (df["sma_short"] > df["sma_long"]).astype(int)   # 당일 SMA 기준
df["strategy_return"] = df["signal"] * df["daily_return"] - cost_per_day
```
당일 종가로 계산된 signal을 당일 return에 곱함. 올바른 구현은 `df["signal"].shift(1)` 사용. MACD·RSI는 `shift(1)` 적용 완료. SMA만 누락.

---

**#2 — 전략 인스턴스 캐시 kwargs 무시 (`strategy/registry.py:26-28`)**

```python
if name not in _instance_cache:
    _instance_cache[name] = _REGISTRY[name](**kwargs)
return _instance_cache[name]   # kwargs 변경 시에도 캐시된 인스턴스 반환
```
첫 번째 요청으로 `sma_cross(short_window=10, long_window=30)` 생성 후, 이후 `sma_cross(short_window=5, long_window=20)` 요청도 첫 번째 인스턴스를 그대로 반환. 사용자는 파라미터를 바꿔도 결과가 바뀌지 않는 silent failure를 경험.

---

**#3 — Survivorship bias (`data/universe.py:28,31`)**

```python
last_date = all_dates.max()   # as_of 무시
snapshot = df.loc[last_date]
```
`as_of` 파라미터를 시그니처에 받지만 실제로는 사용하지 않고 데이터셋의 최종일 기준으로 universe를 반환. 중간에 상장폐지된 종목(예: GAMMA)이 전체 기간에서 제외됨. `test_backtest.py:55-76` 테스트가 이 버그를 문서화하며 현재 실패 상태.

---

**#4 — Sharpe ratio 미연환산 (`metrics/performance.py:29`)**

```python
return float(excess.mean() / excess.std())   # sqrt(252) 없음
```
일별 Sharpe를 연환산 없이 반환. 연환산 값의 약 6.3% 수준(1/sqrt(252))으로 과소 보고. `test_metrics.py:15-35`가 이 버그를 명시적으로 검증하며 현재 실패 상태.

---

**#5 — MACD signal 기본값 버그 (`strategy/macd.py:22`)**

```python
signal: int = settings.MACD_SLOW,   # 26 — MACD_SIGNAL(9) 이어야 함
```
MACD signal 평활화 기간이 기본값 9 대신 26으로 설정됨. MACD line과 signal line이 동일한 span을 사용하게 되어 교차 신호가 거의 발생하지 않음.

---

**#6·#7 — 파라미터 디스패치 누락 (`main.py:88-91, 124-125`)**

`/api/backtest`에서 `macd`·`rsi` 요청 시 kwargs가 `{}`로 전달되어 전략별 설정 파라미터가 모두 기본값으로 고정됨. `/api/compare`에서는 `short_window`·`long_window`를 macd·rsi에도 전달하지만, 해당 전략들은 이 키 이름을 사용하지 않아 TypeError 없이 무시됨 (Python kwargs는 알 수 없는 키를 `**kwargs` 없이 수신하면 TypeError 발생 — 단, 전략 생성자가 `**kwargs`를 받지 않으므로 실제로는 TypeError가 발생할 수 있음).

---

**#8 — Worker restart 정책 (`docker-compose.yml:32`)**

```yaml
restart: "no"
```
워커가 예외로 종료되면 재시작되지 않아 큐에 쌓인 모든 작업이 처리되지 않음. `restart: unless-stopped` 또는 `on-failure`로 변경 필요.

---

**#9 — `emit()` await 누락 (`runner/backtest.py:77`)**

```python
emit(run_id, "complete", 100)   # await 없음
```
`emit`은 `async def` 코루틴. `await` 없이 호출하면 coroutine 객체만 생성되고 실행되지 않아 완료 상태가 `_state`에 기록되지 않음. SSE 스트림이 완료 이벤트를 받지 못하고 timeout(180초)까지 대기.

---

**#10·#11 — 동시성 버그**

`runner/backtest.py`의 `_ticker_returns` 전역 리스트와 `runner/progress.py`의 `_cursor` 전역 문자열은 모두 모듈 수준 상태. `/api/compare`에서 `asyncio.gather`로 여러 backtest가 동시 실행될 때 각 run의 ticker returns가 서로 섞이고, SSE 이벤트가 다른 클라이언트에게 전달될 수 있음.

---

### 종합 판단

**신뢰 가능 여부**: No

**이유**: Sharpe ratio 미연환산(#4)과 SMA lookahead bias(#1)로 인해 모든 성과 지표가 잘못 계산되며, 전략 인스턴스 캐시(#2)와 survivorship bias(#3)로 인해 파라미터 변경 및 universe 구성 자체가 올바르게 동작하지 않는다. Critical 버그 4건이 동시에 존재하여 현재 상태에서 백테스트 결과를 연구 목적으로도 신뢰하기 어렵다.
