# audit-concurrency 결과 — 2026-03-16

### 요약
| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | 3 |
| 🟠 High | 2 |
| 🟡 Medium | 2 |
| 🟢 Low | 1 |

---

### 발견 항목

| # | 항목 | 파일:라인 | 문제 요약 | 심각도 |
|---|------|----------|----------|--------|
| 1 | SSE 공유 커서 크로스토킹 | `runner/progress.py:19,27,42` | `_cursor`가 모든 run_id에 공유되어 run-A의 이벤트가 run-B 구독자에게 전달됨 | 🔴 Critical |
| 2 | `_ticker_returns` 전역 가변 리스트 | `runner/backtest.py:23,43,56,67` | 모듈 레벨 리스트를 `global`로 재사용 — 동시 백테스트 실행 시 여러 run의 결과가 섞임 | 🔴 Critical |
| 3 | 전략 인스턴스 캐시 kwargs 무시 | `strategy/registry.py:26-28` | `_instance_cache`가 name만으로 캐싱 — 다른 파라미터로 요청해도 첫 번째 인스턴스 반환 | 🔴 Critical |
| 4 | `emit()` await 누락 | `runner/backtest.py:77` | 마지막 `emit(run_id, "complete", 100)` 호출에서 `await` 누락 — complete 이벤트가 실제로 전송되지 않음 | 🟠 High |
| 5 | 동시 비교 실행 시 전역 상태 충돌 | `runner/dispatcher.py:27-34` | `run_comparison`이 `asyncio.gather`로 `run_backtest`를 병렬 실행하나 `_ticker_returns`(#2)와 `_cursor`(#1)가 공유 — 결과 오염 확정 | 🟠 High |
| 6 | Redis 결과 TTL 미설정 | `storage/result_store.py:39` | `client.set(...)` 호출에 `ex=` 인자 없음 — 결과가 Redis에 영구 누적되어 장시간 운영 시 메모리 증가 | 🟡 Medium |
| 7 | SSE 상태 정리 미구현 | `runner/progress.py:17,31-51` | run이 완료된 후 `_state[run_id]` 항목이 삭제되지 않음 — 장시간 운영 시 인메모리 누수 | 🟡 Medium |
| 8 | Worker 단일 루프, 재처리 없음 | `worker.py:33-51` | 예외를 catch해 error 결과를 저장하지만 실패 job을 큐에 재투입하지 않으며, worker 프로세스 자체가 죽으면 재시작 메커니즘 없음 | 🟢 Low |

---

### 상세 설명

#### #1 — SSE 공유 커서 크로스토킹 (Critical)

`runner/progress.py`의 `_cursor`는 단일 전역 문자열이다.

```python
# progress.py:19
_cursor: str = ""

# emit() 내부 — 모든 run_id가 동일 변수에 덮어씀
_cursor = f"data: {json.dumps(payload)}\n\n"   # line 27

# stream() 내부 — run_id 검증 없이 _cursor를 그대로 yield
yield _cursor   # line 42
```

run-A와 run-B가 동시에 실행되면 `emit`이 교차 호출되면서 `_cursor`가 계속 덮어써진다. run-B를 구독 중인 클라이언트가 run-A의 ticker 진행률 이벤트를 수신하게 된다. 올바른 구현은 `yield f"data: {json.dumps(_state[run_id])}\n\n"` 처럼 `_state[run_id]`에서 직접 읽어야 한다.

#### #2 — `_ticker_returns` 전역 가변 리스트 (Critical)

```python
# backtest.py:23
_ticker_returns: list[pd.Series] = []

# run_backtest() 내부
global _ticker_returns   # line 43
_ticker_returns = []     # line 56 — 새로운 run 시작마다 초기화
_ticker_returns.append(result_df["strategy_return"].rename(ticker))  # line 67
```

`run_comparison`이 `asyncio.gather`로 두 `run_backtest` 코루틴을 동시에 실행하면, 코루틴 A가 `_ticker_returns = []`로 초기화한 직후 코루틴 B도 같은 초기화를 수행하거나, A의 append 결과를 B가 다시 초기화로 지워버린다. 결과적으로 portfolio 계산에 잘못된 ticker 데이터가 섞인다.

#### #3 — 전략 인스턴스 캐시 kwargs 무시 (Critical)

```python
# registry.py:26-28
if name not in _instance_cache:
    _instance_cache[name] = _REGISTRY[name](**kwargs)
return _instance_cache[name]
```

캐시 키가 `name`만이다. 첫 번째 요청이 `sma_cross(short_window=20, long_window=50)`으로 캐시를 생성한 뒤, 두 번째 요청이 `sma_cross(short_window=5, long_window=10)`으로 오면 **파라미터가 다름에도 첫 번째 인스턴스를 반환**한다. 백테스트 결과가 파라미터와 무관하게 동일해져 연구 결과 자체를 신뢰할 수 없게 된다.

#### #4 — `emit()` await 누락 (High)

```python
# backtest.py:77
emit(run_id, "complete", 100)   # await 없음
```

`emit`은 `async def`이므로 호출만 하면 코루틴 객체가 생성되고 즉시 GC된다. "complete" 이벤트는 `_state`에 기록되지 않고 SSE 스트림에도 전달되지 않는다. 클라이언트는 180초 타임아웃까지 대기하다 강제 종료 이벤트를 받게 된다.

#### #5 — 동시 비교 실행 시 전역 상태 충돌 (High)

`dispatcher.py`의 `run_comparison`은 `asyncio.gather`로 여러 `run_backtest`를 병렬 실행한다. 이는 #1(공유 `_cursor`)과 #2(공유 `_ticker_returns`) 버그를 **의도적으로 트리거**하는 구조다. `/api/compare` 엔드포인트를 호출하면 두 버그가 동시에 발현된다.

#### #6 — Redis 결과 TTL 미설정 (Medium)

`result_store.py:39`의 `client.set(f"result:{run_id}", ...)` 호출에 `ex` 또는 `px` 인자가 없다. 모든 백테스트 결과가 Redis에 영구 보존되어 장시간 운영 시 메모리가 선형 증가한다.

#### #7 — SSE 상태 정리 미구현 (Medium)

`_state` dict에 run_id 항목이 추가되지만 run 완료 후 삭제 코드가 없다. API 프로세스가 장시간 실행되면 완료된 모든 run의 상태가 메모리에 누적된다.

#### #8 — Worker 재처리 메커니즘 없음 (Low)

`worker.py`는 예외 발생 시 error 결과를 Redis에 저장하고 다음 job으로 넘어간다. 실패한 job을 Dead Letter Queue에 보내거나 재시도하는 로직이 없다. 또한 worker 프로세스 자체가 비정상 종료되면 Docker Compose `restart: always` 같은 외부 재시작 설정에만 의존한다.

---

### 종합 판단

**신뢰 가능 여부**: No

**이유**: 전략 인스턴스 캐시가 kwargs를 무시하므로 파라미터가 다른 백테스트도 동일한 인스턴스를 반환하며, `_ticker_returns` 전역 리스트가 동시 실행 시 덮어써져 portfolio 계산 결과가 오염된다. 이 두 가지 Critical 버그만으로도 백테스트 수치 자체를 신뢰할 수 없다.
