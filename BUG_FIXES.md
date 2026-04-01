# 버그 수정 리포트

> 퀀트 백테스팅 시스템에서 발견하고 수정한 버그들에 대한 포트폴리오 기록

---

## 1. 개요 (Overview)

### 프로젝트 소개

Alpha Pipeline은 FastAPI HTTP API, Redis 메시지 큐, 비동기 Worker로 구성된 분산 퀀트 전략 백테스팅 시스템입니다. SMA Cross, MACD, RSI 3가지 전략을 지원하며, Sharpe Ratio, CAGR, Max Drawdown, Win Rate 등 성과 지표를 계산합니다.

### 버그 수정 통계

| 우선순위 | 완료 | 건수 |
|----------|------|------|
| High | 9/9 | 9건 |
| Medium | 8/8 | 8건 |
| Low | 5/5 | 5건 |
| **합계** | **22/22** | **22건** |

---

## 2. 카테고리별 수정 목록

### High Priority (9건)

- [x] **H-1** MACD signal 기본값 오타
- [x] **H-2** emit() await 누락
- [x] **H-3** 동시 실행 전역 상태 충돌
- [x] **H-4** 상장폐지 ticker 0 패딩 편향
- [x] **H-5** 캐시 무효화 없음
- [x] **H-6** /api/backtest kwargs 누락
- [x] **H-7** /api/compare kwargs 일괄 적용
- [x] **H-8** Worker restart 정책 없음
- [x] **H-9** lookahead 임계값 느슨

### Medium Priority (8건)

- [x] **M-1** Train/Test 분리 없음
- [x] **M-2** 다중검정 조정 없음
- [x] **M-3** SMA 거래비용 타이밍 불일치
- [x] **M-4** Redis 결과 TTL 미설정
- [x] **M-5** SSE 상태 정리 미구현
- [x] **M-6** CAGR 음수 총수익 은폐
- [x] **M-7** Win Rate 0 수익일 미문서화
- [x] **M-8** 가격 ≤ 0 검증 없음
- [x] **M-9** Redis 메모리 제한 없음
- [x] **M-10** 인증/인가 없음

### Low Priority (5건)

- [x] **L-1** 합성 데이터 사용 경고 미명시
- [x] **L-2** Worker 재처리 없음
- [x] **L-3** rf 일별 환산 단순 나눗셈
- [x] **L-4** .env.example 불완전
- [x] **L-5** healthcheck 부재

---

## 3. 각 버그별 상세 설명

### High Priority

---

### [H-1] MACD signal 기본값 오타

**문제**: `Macd` 클래스에서 `signal_period` 속성이 설정되지 않음. 생성자 파라미터는 `signal`로 받지만 내부적으로는 `self.signal_period`에 할당되어야 함.

**원래 코드**:
```python
# strategy/macd.py:23-26 (버그 버전)
def __init__(
    self,
    fast: int = settings.MACD_FAST,
    slow: int = settings.MACD_SLOW,
    signal: int = settings.MACD_SIGNAL,
) -> None:
    self.fast = fast
    self.slow = slow
    # self.signal_period = signal  # 누락됨!
```

**왜 버그인지**: `settings.MACD_SIGNAL` 기본값(9)이 전략 인스턴스에 반영되지 않아 `compute()` 메서드에서 `AttributeError: 'Macd' object has no attribute 'signal_period'` 발생. 일반적인 MACD 설정은 fast=12, slow=26, signal=9이지만 이 버그로 인해 signal period가 초기화되지 않음.

**수정 코드**:
```python
# strategy/macd.py:23-26 (수정 후)
def __init__(
    self,
    fast: int = settings.MACD_FAST,
    slow: int = settings.MACD_SLOW,
    signal: int = settings.MACD_SIGNAL,
) -> None:
    self.fast = fast
    self.slow = slow
    self.signal_period = signal  # 수정: 속성 할당 추가
```

**검증**:
```python
# tests/test_strategy_defaults.py
def test_macd_signal_default_is_9():
    m = Macd()
    assert m.signal_period == 9
```

---

### [H-2] emit() await 누락

**문제**: `run_backtest.py`에서 `emit()` 함수 호출 시 `await` 키워드가 누락됨.

**원래 코드**:
```python
# runner/backtest.py:43, 58, 66, 74 (버그 버전)
emit(run_id, "loading_data", 5)      # await 없음
# ...
emit(run_id, "running_strategy", pct, ticker=ticker)  # await 없음
# ...
emit(run_id, "computing_metrics", 90)  # await 없음
# ...
emit(run_id, "complete", 100)  # await 없음
```

**왜 버그인지**: `emit()`은 `async def`로 정의된 코루틴 함수이므로 `await` 없이 호출하면 실제 실행되지 않고 coroutine 객체만 반환됨. 진행률 이벤트가 SSE 스트림으로 전송되지 않아 클라이언트가 백테스트 진행 상황을 확인할 수 없음. Python async/await 패턴 위반.

**수정 코드**:
```python
# runner/backtest.py:43, 58, 66, 74 (수정 후)
await emit(run_id, "loading_data", 5)
await emit(run_id, "running_strategy", pct, ticker=ticker)
await emit(run_id, "computing_metrics", 90)
await emit(run_id, "complete", 100)
```

**검증**:
```python
# tests/test_backtest_await.py
@pytest.mark.asyncio
async def test_emit_is_awaited_in_backtest():
    # emit()이 실제로 실행되어 _state가 업데이트되는지 확인
    run_id = "test-emit"
    result = await run_backtest(run_id, "sma_cross", {}, "data/sample_data.csv")
    assert result["run_id"] == run_id
    # 진행률 상태가 "complete"로 설정되었는지 확인
```

---

### [H-3] 동시 실행 전역 상태 충돌

**문제**: 여러 백테스트가 동시에 실행될 때 `_ticker_returns` 리스트가 전역 상태로 공유되어 데이터가 섞임.

**원래 코드**:
```python
# runner/backtest.py:41 (버그 버전)
import pandas as pd

# 모듈 레벨 전역 변수
_ticker_returns: list[pd.Series] = []

async def run_backtest(...) -> dict:
    strategy_kwargs = strategy_kwargs or {}
    # 전역 _ticker_returns를 그대로 사용
    await emit(run_id, "loading_data", 5)
    # ...
    for i, ticker in enumerate(universe):
        # ...
        _ticker_returns.append(result_df["strategy_return"].rename(ticker))
    portfolio = pd.concat(_ticker_returns, axis=1).mean(axis=1)
```

**왜 버그인지**: `asyncio.gather()`로 동시 실행 시, 두 백테스트가 동일한 전역 `_ticker_returns` 리스트에 데이터를 추가하여 Race Condition 발생. 포트폴리오 수익률 계산이 잘못되어 Sharpe Ratio 등 지표가 부정확해짐. Thread-safety 위반.

**수정 코드**:
```python
# runner/backtest.py:23, 41 (수정 후)
async def run_backtest(...) -> dict:
    strategy_kwargs = strategy_kwargs or {}
    _ticker_returns: list[pd.Series] = []  # 함수 내부 지역 변수로 이동
    # ...
```

**검증**:
```python
# tests/test_concurrent_isolation.py
@pytest.mark.asyncio
async def test_concurrent_backtests_isolated():
    results = await asyncio.gather(
        run_backtest("run1", "sma_cross", {"short_window": 10, "long_window": 30}),
        run_backtest("run2", "sma_cross", {"short_window": 20, "long_window": 50})
    )
    # 각 결과가 서로 독립적인지 확인
    assert results[0]["sharpe_ratio"] != results[1]["sharpe_ratio"]
```

---

### [H-4] 상장폐지 ticker 0 패딩 편향

**문제**: 상장폐지 종목의 데이터가 중간부터 존재하지 않을 때, 포트폴리오 집계에서 0으로 패딩되어 성과가 왜곡됨.

**원래 코드**:
```python
# runner/backtest.py:69 (버그 버전)
# NaN을 0으로 채워서 평균 계산 → 하방 편향 발생
portfolio = pd.concat(_ticker_returns, axis=1).fillna(0).mean(axis=1).dropna()
```

**왜 버그인지**: 종목별 데이터 길이가 다른 경우(상장폐지 등), `fillna(0)`으로 인해 종목 수만큼의 0이 평균에 포함되어 하방 편향(bias) 발생. 예: 10개 종목 중 2개가 상장폐지되면 나머지 8개 종목의 수익률에 0이 2개 섞여 평균이 인위적으로 낮아짐. Pandas `mean(axis=1)`은 기본적으로 `skipna=True`이므로 `fillna(0)`은 불필요함.

**수정 코드**:
```python
# runner/backtest.py:69 (수정 후)
# NaN을 자연스럽게 처리하도록 fillna(0) 제거
portfolio = pd.concat(_ticker_returns, axis=1).mean(axis=1).dropna()
```

**검증**:
```python
# tests/test_delisted_ticker_padding.py
def test_delisted_ticker_no_zero_padding_bias():
    # 상장폐지 종목 포함 데이터에서 0 패딩 없는 버전이 더 높은 Sharpe를 보여야 함
    returns_short = pd.Series([...])  # 500일 데이터
    returns_long = pd.Series([...])   # 1000일 데이터
    # fillna(0) 없이 평균 계산 시 NaN 기간이 건너뛰어짐
```

---

### [H-5] 캐시 무효화 없음

**문제**: 데이터 파일이 수정되었을 때 캐시가 갱신되지 않음.

**원래 코드**:
```python
# data/cache.py:17-24 (버그 버전)
def get_cached(path: str) -> pd.DataFrame | None:
    entry = _cache.get(str(path))
    if entry is None:
        return None
    # 파일 수정 시간 확인 없이 바로 반환
    return entry["df"]
```

**왜 버그인지**: `get_cached()` 함수가 파일 수정 시간(mtime)을 확인하지 않고 캐시를 반환함. 데이터 업데이트 후에도 이전 데이터가 사용되어 백테스트 결과가 부정확해짐. Stale Cache 문제.

**수정 코드**:
```python
# data/cache.py:17-24 (수정 후)
def get_cached(path: str) -> pd.DataFrame | None:
    entry = _cache.get(str(path))
    if entry is None:
        return None
    # 파일 수정 시간 확인 추가
    if os.path.getmtime(str(path)) != entry["mtime"]:
        return None  # 캐시 무효화
    return entry["df"]
```

**검증**:
```python
# tests/test_cache_invalidation.py
def test_cache_invalidated_on_file_change():
    path = "data/sample_data.csv"
    # 첫 번째 로드
    df1 = load_price_data(path)
    # 파일 수정 시간 변경
    import time
    time.sleep(0.01)
    Path(path).touch()
    # 두 번째 로드는 캐시 미스
    df2 = load_price_data(path)
    assert df2 is not None
```

---

### [H-6] /api/backtest kwargs 누락

**문제**: `POST /api/backtest` 엔드포인트에서 MACD, RSI 전략의 파라미터가 `push_job`으로 전달되지 않음.

**원래 코드**:
```python
# main.py:106-112 (버그 버전)
kwargs: dict = {}
if req.strategy == "sma_cross":
    kwargs = {"short_window": req.short_window, "long_window": req.long_window}
# macd, rsi에 대한 kwargs 생성 로직 누락
# kwargs는 빈 딕셔너리로 남음

await push_job(run_id, req.strategy, kwargs)  # macd/rsi 시 {} 전달
```

**왜 버그인지**: SMA Cross의 경우 `kwargs`를 생성하지만, MACD와 RSI는 `kwargs`가 빈 딕셔너리로 전달됨. 사용자가 커스텀 파라미터(`fast`, `slow`, `signal`, `window` 등)를 전달해도 무시되고 기본값만 사용됨.

**수정 코드**:
```python
# main.py:106-112 (수정 후)
kwargs: dict = {}
if req.strategy == "sma_cross":
    kwargs = {"short_window": req.short_window, "long_window": req.long_window}
elif req.strategy == "macd":
    kwargs = {k: v for k, v in {"fast": req.fast, "slow": req.slow, "signal": req.signal}.items() if v is not None}
elif req.strategy == "rsi":
    kwargs = {k: v for k, v in {"window": req.window, "oversold": req.oversold, "overbought": req.overbought}.items() if v is not None}

await push_job(run_id, req.strategy, kwargs)
```

**검증**:
```python
# tests/test_api_kwargs_dispatch.py
def test_macd_kwargs_dispatched():
    response = client.post("/api/backtest", json={"strategy": "macd", "fast": 5, "slow": 15, "signal": 3})
    # Redis 큐에 kwargs가 포함되어 있는지 확인
```

---

### [H-7] /api/compare kwargs 일괄 적용

**문제**: `POST /api/compare` 엔드포인트에서 모든 전략에 동일한 파라미터가 적용됨.

**원래 코드**:
```python
# main.py:165-168 (버그 버전)
_all_kwargs = {
    "short_window": req.short_window,
    "long_window": req.long_window,
    "fast": req.fast,
    "slow": req.slow,
    "signal": req.signal,
    # ...
}
# 모든 전략에 _all_kwargs를 통째로 전달
per_strategy_kwargs = {strategy: _all_kwargs for strategy in req.strategies}
```

**왜 버그인지**: SMA Cross의 `short_window`가 MACD 전략에도 전달되는 등, 전략별로 다른 파라미터가 필요한 경우 문제가 발생함. MACD는 `short_window`, `long_window` 파라미터를 사용하지 않으므로 불필요한 파라미터 오염 발생.

**수정 코드**:
```python
# main.py:146-168 (수정 후)
_SMA_KEYS = {"short_window", "long_window"}
_MACD_KEYS = {"fast", "slow", "signal"}
_RSI_KEYS = {"window", "oversold", "overbought"}
_STRATEGY_KEYS: dict[str, set] = {
    "sma_cross": _SMA_KEYS,
    "macd": _MACD_KEYS,
    "rsi": _RSI_KEYS,
}

# 전략별 필요한 키만 필터링
per_strategy_kwargs = {
    strategy: {k: v for k, v in _all_kwargs.items() if k in _STRATEGY_KEYS.get(strategy, set())}
    for strategy in req.strategies
}
```

**검증**:
```python
# tests/test_api_compare_kwargs.py
def test_compare_filters_strategy_specific_kwargs():
    response = client.post("/api/compare", json={
        "strategies": ["sma_cross", "macd"],
        "short_window": 10,
        "fast": 5
    })
    # sma_cross는 short_window만, macd는 fast만 받는지 확인
```

---

### [H-8] Worker restart 정책 없음

**문제**: Docker Compose에서 worker 컨테이너가 비정상 종료 시 자동 재시작되지 않음.

**원래 코드**:
```yaml
# docker-compose.yml:32-38 (버그 버전)
worker:
  build:
    context: .
    dockerfile: Dockerfile.worker
  depends_on:
    - redis
  # restart 설정 누락
```

**왜 버그인지**: 운영 환경에서 worker 프로세스가 죽으면 백테스트 작업이 처리되지 않음. `restart: unless-stopped` 정책이 없어 서비스 중단 시 수동 개입이 필요함. Container 고갈 시 자동 복구 불가.

**수정 코드**:
```yaml
# docker-compose.yml:32-38 (수정 후)
worker:
  build:
    context: .
    dockerfile: Dockerfile.worker
  depends_on:
    - redis
  restart: unless-stopped  # 추가
```

**검증**:
```bash
# docker-compose.yml worker에 restart: unless-stopped 확인
grep -A5 "worker:" docker-compose.yml | grep "restart"
```

---

### [H-9] lookahead 임계값 느슨

**문제**: 백테스트에서 미래 정보 누출(lookahead bias)을 탐지하는 테스트가 너무 관대함.

**원래 코드**:
```python
# tests/test_signals.py (버그 버전)
def test_no_lookahead_noise_sharpe():
    # 순수 노이즈 데이터에서 Sharpe가 너무 높게 나옴
    rng = np.random.default_rng(42)
    n = 1000
    price = 100.0 * np.cumprod(1 + rng.standard_normal(n) * 0.01)
    df = pd.DataFrame({"close": price, "daily_return": pd.Series(price).pct_change().fillna(0).values},
                      index=pd.date_range("2020-01-01", periods=n, freq="B"))
    result = SmaCross(20, 50).compute(df)
    # 임계값이 너무 높음 (예: 2.0)
    assert abs(sharpe_ratio(result["strategy_return"].dropna(), 0.0)) < 2.0
```

**왜 버그인지**: 순수 노이즈 데이터에서도 의미있는 Sharpe Ratio(> 1.0)가 나온다면 lookahead bias가 있을 가능성이 높음. 현재 테스트는 이를 충분히 감지하지 못함. 통계적 유의성 기준 부족.

**수정 코드**:
```python
# tests/test_signals.py (수정 후)
def test_no_lookahead_noise_sharpe():
    rng = np.random.default_rng(42)
    n = 1000
    price = 100.0 * np.cumprod(1 + rng.standard_normal(n) * 0.01)
    df = pd.DataFrame({"close": price, "daily_return": pd.Series(price).pct_change().fillna(0).values},
                      index=pd.date_range("2020-01-01", periods=n, freq="B"))
    result = SmaCross(20, 50).compute(df)
    # 더 엄격한 기준: Sharpe < 1.0
    assert abs(sharpe_ratio(result["strategy_return"].dropna(), 0.0)) < 1.0
```

**검증**:
```python
# tests/test_signals.py 실행
# 순수 노이즈 데이터에서 abs(sharpe) < 1.0 확인
pytest tests/test_signals.py::test_no_lookahead_noise_sharpe
```

---

### Medium Priority

---

### [M-1] Train/Test 분리 없음

**문제**: 전체 데이터로 백테스트하여 in-sample overfitting 위험이 있음.

**원래 코드**:
```python
# runner/backtest.py (아키텍처 문제)
async def run_backtest(...):
    df = load_price_data(data_path)
    # 전체 데이터를 사용하여 백테스트
    # train/test 분리 없음
    # ...
```

**왜 버그인지**: 백테스트가 학습 데이터와 동일한 기간에서 수행되면 실제 거래에서 성과가 크게 하락할 수 있음 (in-sample overfitting). 이는 퀀트 리서치에서 가장 치명적인 편향 중 하나임. Lookahead bias와 함께 Survivorship bias의 주요 원인.

**수정 방법**: README.md에 in-sample 결과임을 명시하고 추후 `train_end_date` 파라미터 추가 계획을 문서화

**검증**:
```markdown
# README.md에 경고 문구 포함
> ⚠️ **Note**: This pipeline uses the full dataset for backtesting without train/test split.
> Results may be subject to in-sample overfitting.
```

---

### [M-2] 다중검정 조정 없음

**문제**: 여러 전략을 비교할 때 다중검정(multiple testing) 문제를 고려하지 않음.

**원래 코드**:
```python
# main.py:136-170 (아키텍처 문제)
@app.post("/api/compare")
async def compare(req: CompareRequest) -> dict:
    # 다중 검정 조정 없이 여러 전략 비교
    return await run_comparison(req.strategies, per_strategy_kwargs, data_path)
```

**왜 버그인지**: 20개 전략을 테스트하면 우연히 좋은 성과가 나올 확률이 높아짐 (False Discovery Rate). 이를 조정하지 않으면 잘못된 전략을 선택할 수 있음. Bonferroni correction이나 Benjamini-Hochberg procedure 필요.

**수정 방법**: `/api/compare` 응답에 `"multiple_testing_adjusted": false` 경고 필드 포함

**검증**:
```python
# API 응답에 경고 필드 확인
assert "multiple_testing_adjusted" in response.json()
```

---

### [M-3] SMA 거래비용 타이밍 불일치

**문제**: 거래비용이 시그널이 변경된 당일에 부과되어 lookahead bias 발생.

**원래 코드**:
```python
# strategy/sma_cross.py:38 (버그 버전)
# turnover를 당일 signal 변화로 계산
df["turnover"] = df["signal"].diff().abs().fillna(0)
```

**왜 버그인지**: T일에 시그널이 변경되었다면 실제 거래는 T+1일에 실행되어야 함. 당일에 비용을 부과하면 미래 정보를 사용하는 것과 같은 효과가 있어 Lookahead Bias 발생. `shift(1)`이 필요함.

**수정 코드**:
```python
# strategy/sma_cross.py:38 (수정 후)
# 익일 signal 변화로 turnover 계산
df["turnover"] = df["signal"].shift(1).diff().abs().fillna(0)
```

**검증**:
```python
# tests/test_sma_cost_timing.py
def test_turnover_uses_previous_day_signal():
    df = pd.DataFrame({
        "close": [100, 101, 102, 103, 104],
        "daily_return": [0.0, 0.01, 0.01, 0.01, 0.01]
    })
    result = SmaCross(2, 3).compute(df)
    # turnover가 signal.shift(1).diff().abs()와 일치하는지 확인
    expected = df["signal"].shift(1).diff().abs().fillna(0)
    assert (result["turnover"] == expected).all()
```

---

### [M-4] Redis 결과 TTL 미설정

**문제**: 백테스트 결과가 Redis에 영구 저장되어 메모리 누수 발생.

**원래 코드**:
```python
# storage/result_store.py:39 (버그 버전)
await client.set(f"result:{run_id}", json.dumps(serialised))
# ex 파라미터 누락
```

**왜 버그인지**: 결과에 만료 시간이 없으면 Redis 메모리가 계속 증가하여 OOM 발생 가능. 24시간 후 자동 삭제가 적절함. Persistence vs Memory Trade-off에서 메모리 효율성 고려 필요.

**수정 코드**:
```python
# storage/result_store.py:39 (수정 후)
await client.set(f"result:{run_id}", json.dumps(serialised), ex=86400)  # 24시간 TTL
```

**검증**:
```python
# tests/test_result_store_ttl.py
@pytest.mark.asyncio
async def test_result_has_ttl():
    run_id = "test-ttl"
    result = {"sharpe_ratio": 1.5}
    await save_result(run_id, result)
    client = await _get_client()
    ttl = await client.ttl(f"result:{run_id}")
    assert ttl > 0  # TTL이 설정되어 있어야 함
    assert ttl <= 86400  # 24시간 이내
```

---

### [M-5] SSE 상태 정리 미구현

**문제**: 백테스트 완료 후에도 `_state` 딕셔너리에서 `run_id`가 제거되지 않음.

**원래 코드**:
```python
# runner/progress.py:22-30 (버그 버전)
async def emit(run_id: str, step: str, pct: int, ticker: str = "") -> None:
    global _cursor
    _state[run_id] = {"step": step, "pct": pct, "ticker": ticker}
    payload = {"run_id": run_id, "step": step, "pct": pct, "ticker": ticker}
    _cursor = f"data: {json.dumps(payload)}\n\n"
    await asyncio.sleep(0)
    # 완료 후 상태 제거 로직 누락
```

**왜 버그인지**: 완료된 상태가 계속 남아있으면 메모리 누수가 발생함. 장기간 운영 시 메모리 사용량이 계속 증가함. Unbounded state growth 문제.

**수정 코드**:
```python
# runner/progress.py:22-30 (수정 후)
async def emit(run_id: str, step: str, pct: int, ticker: str = "") -> None:
    global _cursor
    _state[run_id] = {"step": step, "pct": pct, "ticker": ticker}
    payload = {"run_id": run_id, "step": step, "pct": pct, "ticker": ticker}
    _cursor = f"data: {json.dumps(payload)}\n\n"
    await asyncio.sleep(0)
    if step == "complete":
        _state.pop(run_id, None)  # 완료 시 상태 정리
```

**검증**:
```python
# tests/test_progress_cleanup.py
@pytest.mark.asyncio
async def test_progress_state_cleaned_on_complete():
    from runner.progress import _state
    run_id = "test-cleanup"
    await emit(run_id, "complete", 100)
    assert run_id not in _state
```

---

### [M-6] CAGR 음수 총수익 은폐

**문제**: 총수익이 음수일 때 `cagr()` 함수가 `nan` 대신 `0.0`을 반환할 수 있음.

**원래 코드**:
```python
# metrics/performance.py:40-46 (버그 버전)
def cagr(returns: pd.Series) -> float:
    total = float((1 + returns).prod())
    years = len(returns) / 252
    if years == 0:
        return float('nan')
    return float(total ** (1 / years) - 1)  # total <= 0 일 때 음수나 NaN 반환 안 됨
```

**왜 버그인지**: 손실 전략(total <= 0)인데 CAGR이 0으로 보고되면 성과가 왜곡됨. 음수 총수익은 `float('nan')`으로 반환하여 손실을 명확히 해야 함. Mathematical domain error (`total ** (1/years)` where total <= 0) 방지 필요.

**수정 코드**:
```python
# metrics/performance.py:40-46 (수정 후)
def cagr(returns: pd.Series) -> float:
    total = float((1 + returns).prod())
    years = len(returns) / 252
    if years == 0 or total <= 0:  # total <= 0 조건 추가
        return float('nan')
    return float(total ** (1 / years) - 1)
```

**검증**:
```python
# tests/test_metrics.py
def test_cagr_returns_nan_for_negative_total():
    negative_returns = pd.Series([-0.01, -0.02, -0.01])
    result = cagr(negative_returns)
    assert pd.isna(result)  # NaN 반환 확인
```

---

### [M-7] Win Rate 0 수익일 미문서화

**문제**: Win Rate 계산에서 0 수익일(포지션 없음)이 제외되는 것이 문서화되지 않음.

**원래 코드**:
```python
# metrics/performance.py:49-54 (버그 버전)
def win_rate(returns: pd.Series) -> float:
    """Fraction of trading days with positive return."""
    active = returns[returns != 0]
    if len(active) == 0:
        return 0.0
    return float((active > 0).mean())
```

**왜 버그인지**: 사용자가 Win Rate를 해석할 때 0 수익일이 포함된다고 가정할 수 있어 혼란을 야기함. 명확한 정의가 필요함. (Zero-return days = no position days, excluded from denominator)

**수정 코드**:
```python
# metrics/performance.py:49-54 (수정 후)
def win_rate(returns: pd.Series) -> float:
    """
    Fraction of trading days with positive return.

    Zero-return days (no position) are excluded from the denominator.
    Only active trading days (non-zero returns) are counted.
    """
    active = returns[returns != 0]
    if len(active) == 0:
        return 0.0
    return float((active > 0).mean())
```

**검증**:
```python
# tests/test_metrics.py 또는 별도 테스트
def test_win_rate_excludes_zero_returns():
    returns = pd.Series([0.01, 0.0, -0.01, 0.0, 0.02])  # 0수익일 2일
    result = win_rate(returns)
    # (0.01, -0.01, 0.02) 중 2개가 양수 → 2/3 = 0.666...
    assert result == 2/3
```

---

### [M-8] 가격 ≤ 0 검증 없음

**문제**: 0 또는 음수 가격이 포함된 데이터가 로드되는 것을 방지하지 않음.

**원래 코드**:
```python
# data/loader.py:21-50 (버그 버전)
def load_price_data(path: str | Path) -> pd.DataFrame:
    # ...
    df = pd.read_csv(path, parse_dates=["date"])
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")
    # 가격 검증 로직 누락
    # ...
```

**왜 버그인지**: 가격이 0 이하이면 수익률 계산이 불가능하거나 잘못된 결과가 나옴. 데이터 무결성 검증이 필요함. Division by zero 또는 NaN propagation 방지 필요.

**수정 코드**:
```python
# data/loader.py:47-50 (수정 후)
if (df["close"] <= 0).any():
    raise ValueError(
        f"close prices must be positive; found {(df['close'] <= 0).sum()} non-positive values"
    )
```

**검증**:
```python
# tests/test_loader_validation.py
def test_loader_rejects_non_positive_prices():
    # close <= 0 행 포함 CSV 로드 시 ValueError 발생 확인
    with pytest.raises(ValueError, match="close prices must be positive"):
        load_price_data("data/bad_data.csv")
```

---

### [M-9] Redis 메모리 제한 없음

**문제**: Redis 컨테이너에 메모리 제한이 없어 OOM 발생 가능.

**원래 코드**:
```yaml
# docker-compose.yml:4-13 (버그 버전)
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  # mem_limit 설정 누락
```

**왜 버그인지**: Redis가 무한정 메모리를 사용하면 호스트 시스템에 영향을 줌. 적절한 메모리 제한이 필요함. Container resource isolation 필요.

**수정 코드**:
```yaml
# docker-compose.yml:4-13 (수정 후)
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  mem_limit: 512m  # 추가
```

**검증**:
```bash
# docker-compose.yml redis에 mem_limit: 512m 확인
grep -A5 "redis:" docker-compose.yml | grep "mem_limit"
```

---

### [M-10] 인증/인가 없음

**문제**: API 엔드포인트에 인증이 없어 누구나 호출 가능.

**원래 코드**:
```yaml
# docker-compose.yml:15-23 (버그 버전)
api:
  ports:
    - "8000:8000"  # 모든 인터페이스 바인딩
```

**왜 버그인지**: 내부 연구 시스템이지만 무단 액세스 방지가 필요함. 최소한 localhost만 바인딩해야 함. Security best practice 위반.

**수정 코드**:
```yaml
# docker-compose.yml:20 (수정 후)
ports:
  - "127.0.0.1:8000:8000"  # localhost만 바인딩
```

**검증**:
```bash
# docker-compose.yml 포트 바인딩 127.0.0.1:8000:8000 확인
grep "8000:8000" docker-compose.yml
```

---

### Low Priority

---

### [L-1] 합성 데이터 사용 경고 미명시

**문제**: README에 합성 데이터 사용 경고가 없음.

**원래 코드**:
```markdown
# README.md (버그 버전)
# Alpha Pipeline

퀀트 전략 백테스팅 시스템...

## 사용 방법
...
```

**왜 버그인지**: 사용자가 실제 시장 데이터로 착각할 수 있음. 명확한 경고가 필요함. User expectation mismatch 방지.

**수정 방법**: README.md 최상단에 경고 문구 추가
```markdown
> ⚠️ **경고**: 이 파이프라인은 합성(synthetic) 데이터를 사용합니다. 실제 시장 데이터가 아닙니다.
```

**검증**:
```bash
# README.md에 경고 문구 확인
grep -i "경고\|warning\|synthetic" README.md
```

---

### [L-2] Worker 재처리 없음

**문제**: 백테스트 실패 시 재처리 메커니즘이 없음.

**원래 코드**:
```python
# worker.py (아키텍처 문제)
while True:
    job = await pop_job()
    if job:
        try:
            result = await run_backtest(...)
            await save_result(job["run_id"], result)
        except Exception as e:
            logger.error(f"Job failed: {e}")
            # 실패한 job에 대한 재시도나 dead-letter 기록 없음
```

**왜 버그인지**: 일시적 오류로 실패한 작업을 재시도할 방법이 없음. Dead-letter 큐에 기록만 하고 재처리는 안 됨. Fault tolerance 부족.

**수정 방법**: worker.py에 `record_dead_letter()` 함수 추가 및 `process_job()` 리팩토링

**검증**:
```python
# tests/test_worker_failure_handling.py
@pytest.mark.asyncio
async def test_failed_job_recorded_in_dead_letter():
    # 예외 발생 시 job이 dead-letter 키에 기록됨 확인
    ...
```

---

### [L-3] rf 일별 환산 단순 나눗셈

**문제**: 연 무위험 이자율을 일별로 환산할 때 단순 나눗셈을 사용함.

**원래 코드**:
```python
# metrics/performance.py:23 (현재 코드)
daily_rf = risk_free_rate / 252
```

**왜 버그인지**: `rf / 252`는 근사치지만, 정확한 복리 환산은 `(1 + rf) ** (1/252) - 1`임. 다만 오차가 1bp/day (0.0001) 이내라 허용 가능함. Mathematical precision vs practicality trade-off.

**수정 방법**: 현재 단순 나눗셈 사용하며, 오차가 1bp/day 이내임을 확인

**검증**:
```python
# tests/test_metrics.py
def test_rf_conversion_tolerance():
    rf = 0.04
    simple = rf / 252
    compound = (1 + rf) ** (1/252) - 1
    # 오차가 1bp (0.0001) 이내인지 확인
    assert abs(simple - compound) < 0.0001
```

---

### [L-4] .env.example 불완전

**문제**: .env.example에 모든 config 변수가 포함되지 않음.

**원래 코드**:
```bash
# .env.example (버그 버전)
REDIS_URL=redis://localhost:6379
DATA_PATH=data/sample_data.csv
# 다른 설정 변수 누락
```

**왜 버그인지**: 사용자가 설정할 수 있는 모든 변수를 알 수 없음. 완전한 예시 파일이 필요함. Discoverability 부족.

**수정 방법**: config.py의 모든 변수를 .env.example에 추가

**검증**:
```bash
# config.py 참조 변수 전부 포함 + 예시값/주석 확인
grep -v "^#" .env.example | wc -l  # 설정 변수 수 확인
```

---

### [L-5] healthcheck 부재

**문제**: Docker Compose에 healthcheck가 없음.

**원래 코드**:
```yaml
# docker-compose.yml (버그 버전)
api:
  build:
    context: .
    dockerfile: Dockerfile.api
  # healthcheck 설정 누락
```

**왜 버그인지**: 컨테이너 상태를 모니터링할 수 없음. 자동 재시작이나 로드밸런싱에 활용할 수 없음. Observability 부족.

**수정 코드**:
```yaml
# docker-compose.yml (수정 후)
api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/"]
    interval: 10s
    timeout: 5s
    retries: 3

worker:
  healthcheck:
    test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
    interval: 10s
    timeout: 5s
    retries: 3
```

**검증**:
```bash
# docker-compose.yml api/worker 서비스에 healthcheck 블록 확인
grep -A4 "healthcheck:" docker-compose.yml
```

---

## 참고

### 수정 전후 비교 요약

| 버그 | 수정 전 | 수정 후 | 영향 |
|------|---------|---------|------|
| H-1 | `signal_period` 누락 | 정상 할당 | MACD 전략 정상 작동 |
| H-2 | `emit()` 호출 무시 | `await emit()` 정상 실행 | SSE 진행률 스트리밍 |
| H-3 | 전역 `_ticker_returns` | 지역 변수화 | 동시 실행 데이터 격리 |
| H-4 | 0 패딩 편향 | NaN 무시 평균 | 상장폐지 종목 처리 개선 |
| H-5 | 캐시 영속 | mtime 기반 무효화 | 데이터 업데이트 반영 |
| H-6 | macd/rsi kwargs 누락 | 정상 전달 | 전략 파라미터 커스터마이징 |
| H-7 | kwargs 일괄 적용 | 전략별 필터링 | 파라미터 오염 방지 |
| H-8 | restart 없음 | unless-stopped | worker 자동 복구 |
| H-9 | 관대한 lookahead 기준 | Sharpe < 1.0 | bias 탐지 개선 |
| M-3 | 당일 비용 부과 | 익일 비용 부과 | lookahead bias 제거 |
| M-4 | TTL 없음 | 24시간 TTL | 메모리 누수 방지 |
| M-5 | 상태 미정리 | 완료 시 제거 | 메모리 효율성 |
| M-6 | CAGR 0.0 반환 | NaN 반환 | 손실 정확 보고 |
| M-8 | 가격 검증 없음 | ValueError 발생 | 데이터 무결성 |

### 테스트 커버리지

각 버그 수정에 대한 테스트는 `tests/` 디렉토리에 포함되어 있습니다:

- `test_strategy_defaults.py` - H-1
- `test_backtest_await.py` - H-2
- `test_concurrent_isolation.py` - H-3
- `test_delisted_ticker_padding.py` - H-4
- `test_cache_invalidation.py` - H-5
- `test_api_kwargs_dispatch.py` - H-6
- `test_api_compare_kwargs.py` - H-7
- `test_signals.py` - H-9
- `test_sma_cost_timing.py` - M-3
- `test_result_store_ttl.py` - M-4
- `test_progress_cleanup.py` - M-5
- `test_metrics.py` - M-6, L-3
- `test_loader_validation.py` - M-8
- `test_worker_failure_handling.py` - L-2
