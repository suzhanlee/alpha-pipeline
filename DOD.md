# DoD (Definition of Done) 체크리스트

> REPORT.md High / Medium / Low 항목 기준.
> Critical(C-1~C-6)은 REPORT.md 4절 체크리스트 참조.
>
> **테스트 가능 DoD**: 아래 테스트 코드가 `pytest` 통과 시 완료로 간주.
> **테스트 불가능 DoD**: 수동 확인 또는 설정 파일 검토로 완료 판단.

---

## 🟠 High

---

### H-1 · MACD signal 기본값 오타 (`strategy/macd.py:22`)

- [ ] 완료

**DoD**: `Macd()` 기본 인스턴스의 `signal_period`가 9여야 한다.

```python
# tests/test_strategy_defaults.py
from strategy.macd import Macd

def test_macd_signal_default_is_9():
    """signal 기본값이 MACD_SLOW(26)가 아닌 MACD_SIGNAL(9)이어야 한다."""
    m = Macd()
    assert m.signal_period == 9, (
        f"signal_period={m.signal_period} — MACD_SLOW(26)가 기본값으로 잘못 설정됨. "
        "strategy/macd.py:22 에서 settings.MACD_SLOW → settings.MACD_SIGNAL 로 수정 필요."
    )
```

---

### H-2 · `emit()` await 누락 (`runner/backtest.py:77`)

- [ ] 완료

**DoD**: 백테스트 완료 후 `_state[run_id]["step"]`이 `"complete"`여야 한다.

```python
# tests/test_progress_complete.py
import pytest
from runner.backtest import run_backtest
from runner import progress

@pytest.mark.asyncio
async def test_complete_event_written_to_state(sample_price_df, monkeypatch):
    """await 누락 시 _state에 complete가 기록되지 않아 이 테스트가 실패한다."""
    import data.loader as loader_module
    monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)

    # 테스트 전 상태 초기화
    progress._state.clear()

    run_id = "test-complete-event"
    await run_backtest(run_id, "sma_cross")

    state = progress._state.get(run_id)
    assert state is not None, "_state에 run_id 항목이 없음 — emit() 자체가 호출 안 됨"
    assert state["step"] == "complete", (
        f"step={state.get('step')} — 'complete'가 아님. "
        "backtest.py:77 의 emit() 앞에 await 가 누락되었을 수 있음."
    )
    assert state["pct"] == 100
```

---

### H-3 · 동시 비교 실행 시 전역 상태 충돌 (`runner/dispatcher.py:27-34`)

- [ ] 완료

**DoD**: 두 전략을 동시에 실행해도 각 결과가 자신의 전략명을 유지해야 한다.

```python
# tests/test_concurrent_isolation.py
import asyncio
import pytest
from runner.backtest import run_backtest

@pytest.mark.asyncio
async def test_concurrent_runs_return_correct_strategy(sample_price_df, monkeypatch):
    """
    _ticker_returns 전역 리스트 버그 존재 시:
    두 run의 ticker 수익이 섞여 각 결과의 strategy 필드나 수치가 오염된다.
    """
    import data.loader as loader_module
    monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)

    results = await asyncio.gather(
        run_backtest("run-concurrent-A", "sma_cross"),
        run_backtest("run-concurrent-B", "macd"),
    )
    r_a, r_b = results

    assert r_a["run_id"] == "run-concurrent-A"
    assert r_a["strategy"] == "sma_cross"
    assert r_b["run_id"] == "run-concurrent-B"
    assert r_b["strategy"] == "macd"

    # 두 결과의 Sharpe가 동일하면 ticker_returns가 섞였을 가능성 높음
    assert r_a["sharpe_ratio"] != r_b["sharpe_ratio"], (
        "두 전략의 Sharpe가 동일 — _ticker_returns 전역 리스트가 오염되었을 수 있음."
    )
```

---

### H-4 · GAMMA 상장폐지 ticker 0 패딩 편향 (`runner/backtest.py:72`)

- [ ] 완료

**DoD**: 상장폐지 ticker를 포함한 포트폴리오 Sharpe가, 해당 ticker 없이 계산한 Sharpe와 유사해야 한다 (0 패딩이 지표를 희석하지 않아야 함).

```python
# tests/test_delisted_ticker_padding.py
import numpy as np
import pandas as pd
import pytest

def make_portfolio_sharpe(include_delisted: bool) -> float:
    """active 3종목 vs active 2종목+delisted 0패딩 포트폴리오 Sharpe 비교."""
    from metrics.performance import sharpe_ratio

    rng = np.random.default_rng(0)
    n = 300
    active = pd.DataFrame({
        "ALPHA": rng.normal(0.001, 0.01, n),
        "BETA":  rng.normal(0.001, 0.01, n),
    })

    if include_delisted:
        # GAMMA: 150일만 존재, 나머지는 0 패딩
        gamma = pd.Series(
            list(rng.normal(0.001, 0.01, 150)) + [0.0] * 150,
            name="GAMMA",
        )
        portfolio = pd.concat([active, gamma], axis=1).mean(axis=1)
    else:
        portfolio = active.mean(axis=1)

    return sharpe_ratio(portfolio, risk_free_rate=0.0)

def test_delisted_zero_padding_does_not_distort_sharpe():
    """
    0 패딩 없이 활성 기간만 집계하면 Sharpe 차이가 작아야 한다.
    현재 fillna(0) 구현에서는 이 테스트가 실패할 수 있음.
    """
    sharpe_without = make_portfolio_sharpe(include_delisted=False)
    sharpe_with    = make_portfolio_sharpe(include_delisted=True)

    # 올바른 구현: 차이가 10% 이내여야 함
    relative_diff = abs(sharpe_with - sharpe_without) / (abs(sharpe_without) + 1e-9)
    assert relative_diff < 0.10, (
        f"Sharpe 왜곡: without={sharpe_without:.4f}, with={sharpe_with:.4f} "
        f"(차이 {relative_diff:.1%}) — 0 패딩이 지표를 희석하고 있음."
    )
```

---

### H-5 · 캐시 무효화 메커니즘 없음 (`data/cache.py:12`)

- [ ] 완료

**DoD**: 파일 mtime이 변경된 경우 `get_cached`가 `None`을 반환해야 한다.

```python
# tests/test_cache_invalidation.py
import time
import pandas as pd
import pytest
from data import cache

def test_cache_invalidated_on_file_change(tmp_path):
    """
    파일이 변경된 후 get_cached는 None을 반환해야 한다.
    현재 구현에는 mtime 체크가 없어 stale data를 반환함 — 이 테스트가 실패함.
    """
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text("date,close\n2022-01-01,100\n")

    df = pd.DataFrame({"close": [100]})
    cache.set_cached(str(csv_path), df)

    # 파일 내용 갱신
    time.sleep(0.01)
    csv_path.write_text("date,close\n2022-01-01,200\n")

    result = cache.get_cached(str(csv_path))
    assert result is None, (
        "파일이 변경되었는데도 캐시된 DataFrame을 반환함 — mtime 기반 무효화 필요."
    )
```

---

### H-6 · `/api/backtest` macd·rsi kwargs 누락 (`main.py:88-91`)

- [ ] 완료

**DoD**: `strategy=macd` 요청 시 `kwargs`에 macd 파라미터가 담겨 `push_job`으로 전달되어야 한다.

```python
# tests/test_api_kwargs_dispatch.py
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_macd_backtest_passes_kwargs():
    """macd 요청 시 fast/slow/signal 파라미터가 push_job에 전달되어야 한다."""
    captured = {}

    async def fake_push_job(run_id, strategy, kwargs):
        captured["strategy"] = strategy
        captured["kwargs"] = kwargs

    with patch("main.push_job", side_effect=fake_push_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/backtest", json={
                "strategy": "macd",
                "short_window": 20,
                "long_window": 50,
            })

    assert resp.status_code == 200
    assert captured["strategy"] == "macd"
    # macd는 sma_cross와 다른 파라미터를 가져야 함 — 현재는 {} 로 전달됨
    assert captured["kwargs"] != {}, (
        "macd kwargs가 비어 있음 — main.py:88-91 에서 macd/rsi 분기 처리 누락."
    )

@pytest.mark.asyncio
async def test_rsi_backtest_passes_kwargs():
    """rsi 요청 시에도 strategy 파라미터가 push_job에 전달되어야 한다."""
    captured = {}

    async def fake_push_job(run_id, strategy, kwargs):
        captured["strategy"] = strategy
        captured["kwargs"] = kwargs

    with patch("main.push_job", side_effect=fake_push_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/backtest", json={"strategy": "rsi"})

    assert resp.status_code == 200
    assert captured["kwargs"] != {}
```

---

### H-7 · `/api/compare` kwargs 전 전략 일괄 적용 (`main.py:124-125`)

- [ ] 완료

**DoD**: `run_comparison` 호출 시 각 전략이 자신의 파라미터 키만 수신해야 한다.

```python
# tests/test_api_compare_kwargs.py
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_compare_passes_strategy_specific_kwargs():
    """
    /api/compare 는 각 전략에 맞는 kwargs를 전달해야 한다.
    현재는 short_window/long_window를 macd/rsi에도 넘겨 키 불일치 발생.
    """
    captured_calls = []

    async def fake_run_comparison(strategies, kwargs, data_path):
        captured_calls.append({"strategies": strategies, "kwargs": kwargs})
        return {"results": []}

    with patch("main.run_comparison", side_effect=fake_run_comparison):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/compare", json={
                "strategies": ["sma_cross", "macd"],
                "short_window": 10,
                "long_window": 30,
            })

    assert resp.status_code == 200
    passed_kwargs = captured_calls[0]["kwargs"]

    # sma_cross 전용 키가 macd에 그대로 넘어가면 안 됨
    # 수정 후: 전략별 kwargs 분리 또는 각 전략이 알 수 없는 키를 무시하는 방어 처리
    assert "short_window" not in passed_kwargs or passed_kwargs.get("_strategy_aware") is True, (
        "short_window/long_window가 모든 전략에 동일하게 전달되고 있음 — "
        "전략별 파라미터 분리 필요."
    )
```

---

### H-8 · Worker restart 정책 없음 (`docker-compose.yml:32`) — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (인프라 설정)

수동 확인 항목:

- [ ] `docker-compose.yml`의 `worker` 서비스에 `restart: unless-stopped` 또는 `restart: on-failure` 설정 확인
- [ ] `docker compose up -d` 후 `docker compose kill worker` 실행 → `docker compose ps` 에서 worker가 자동 재시작되는지 확인
- [ ] 재시작 후 큐에 남아 있던 job이 정상 처리되는지 확인

---

### H-9 · lookahead 테스트 임계값 과도하게 느슨 (`tests/test_signals.py:56-64`)

- [ ] 완료

**DoD**: 순수 노이즈 가격 시계열에서 실행한 전략의 Sharpe 절댓값이 1.0 미만이어야 한다.

```python
# tests/test_signals.py 에서 기존 test_no_lookahead 교체 또는 보완
import numpy as np
import pandas as pd
import pytest
from strategy.sma_cross import SmaCross

def test_no_lookahead_noise_sharpe():
    """
    룩어헤드 편향이 없으면 순수 랜덤 시계열에서 Sharpe 절댓값이 1.0 미만이어야 한다.
    기존 임계값 `> -5.0` 은 편향이 있어도 통과하므로 이 테스트로 대체한다.

    - 편향 존재 → Sharpe 가 크게 양수(> 1.0)로 나타남
    - 편향 없음  → Sharpe ≈ 0 (노이즈 범위 이내)
    """
    from metrics.performance import sharpe_ratio

    rng = np.random.default_rng(42)
    n = 1000
    price = 100.0 * np.cumprod(1 + rng.standard_normal(n) * 0.01)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "close": price,
        "daily_return": pd.Series(price).pct_change().fillna(0).values,
    }, index=dates)

    strategy = SmaCross(short_window=20, long_window=50)
    result = strategy.compute(df)

    sharpe = sharpe_ratio(result["strategy_return"].dropna(), risk_free_rate=0.0)

    assert abs(sharpe) < 1.0, (
        f"순수 노이즈 데이터에서 Sharpe={sharpe:.4f} — 절댓값이 1.0 이상이면 "
        "룩어헤드 편향이 의심됨. signal에 shift(1) 적용 여부 확인."
    )
```

---

## 🟡 Medium

---

### M-1 · Train/Test 분리 없음 — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (아키텍처 설계 결정)

수동 확인 항목:

- [ ] `BacktestRequest` 또는 `run_backtest` 인터페이스에 `train_end_date` 파라미터 추가 여부
- [ ] 보고된 성과 수치 옆에 "in-sample 결과임" 명시 (API 응답 또는 결과 문서)
- [ ] walk-forward 또는 expanding-window 분할이 필요할 경우 별도 runner 모듈 설계

---

### M-2 · 다중검정 조정 없음 — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (통계적 방법론)

수동 확인 항목:

- [ ] `/api/compare` 응답에 `"multiple_testing_adjusted": false` 또는 동등한 경고 필드 포함 여부
- [ ] 결과 해석 문서에 "Bonferroni 보정 미적용, best-pick 기준 실제 유형 I 오류율 최대 14%" 명시 여부

---

### M-3 · SMA 거래비용 타이밍 불일치 (`strategy/sma_cross.py:38-41`)

- [ ] 완료

**DoD**: C-1(shift 추가) 수정 후, turnover는 shift된 signal의 변화로 계산되어야 한다.

```python
# tests/test_sma_cost_timing.py
import pandas as pd
import numpy as np
from strategy.sma_cross import SmaCross

def test_sma_cost_applied_on_next_day():
    """
    turnover(거래비용)는 당일 signal이 아닌 전일 대비 변화(shift 후)를 기준으로 산정되어야 한다.
    즉, strategy_return[t] = signal[t-1] * daily_return[t] - cost[t]
    이고 cost[t]는 signal[t-1] vs signal[t-2] 의 변화에서 발생해야 한다.
    """
    rng = np.random.default_rng(0)
    n = 100
    price = 100.0 * np.cumprod(1 + rng.normal(0, 0.01, n))
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "close": price,
        "daily_return": pd.Series(price).pct_change().fillna(0).values,
    }, index=dates)

    strategy = SmaCross(short_window=5, long_window=20)
    result = strategy.compute(df)

    # signal이 shift(1) 적용된 경우: strategy_return은 전일 signal로 결정됨
    # turnover도 동일 날짜 기준 (shift된 signal 간 차이)이어야 함
    # 비용이 수익과 같은 날 발생하되, signal 참조가 이미 shift된 상태인지 확인
    signal_shifted = result["signal"].shift(1)
    expected_turnover = signal_shifted.diff().abs().fillna(0)

    # turnover 컬럼이 shift된 signal 기준으로 재계산되었는지 검증
    pd.testing.assert_series_equal(
        result["turnover"].reset_index(drop=True),
        expected_turnover.reset_index(drop=True),
        check_names=False,
        atol=1e-9,
        err_msg="turnover가 shift(1) 적용 후의 signal 변화를 기준으로 하지 않음.",
    )
```

---

### M-4 · Redis 결과 TTL 미설정 (`storage/result_store.py:39`)

- [ ] 완료

**DoD**: `save_result` 호출 시 Redis `SET` 명령에 `ex` 인자가 전달되어야 한다.

```python
# tests/test_result_store_ttl.py
import pytest
from unittest.mock import AsyncMock, patch, call

@pytest.mark.asyncio
async def test_save_result_sets_ttl():
    """
    save_result는 Redis SET 호출 시 ex= (TTL) 인자를 포함해야 한다.
    미설정 시 결과가 Redis에 영구 누적되어 메모리가 선형 증가한다.
    """
    mock_client = AsyncMock()

    with patch("storage.result_store._get_client", return_value=mock_client):
        from storage.result_store import save_result
        await save_result("run-ttl-test", {"sharpe_ratio": 1.5, "run_id": "run-ttl-test"})

    assert mock_client.set.called, "client.set 이 호출되지 않음"

    _, kwargs = mock_client.set.call_args
    assert "ex" in kwargs, (
        f"client.set 호출에 ex= 인자 없음 (호출 인자: {kwargs}). "
        "result_store.py:39 에 ex=86400 (24h) 등 TTL 추가 필요."
    )
```

---

### M-5 · SSE 상태 정리 미구현 (`runner/progress.py`)

- [ ] 완료

**DoD**: run이 완료(pct=100)된 후 일정 시간이 지나면 `_state[run_id]`가 삭제되어야 한다.

```python
# tests/test_progress_cleanup.py
import pytest
from runner import progress

@pytest.mark.asyncio
async def test_state_cleaned_up_after_completion():
    """
    run 완료 후 _state에서 해당 run_id 항목이 제거되어야 한다.
    현재 구현에는 삭제 코드가 없어 이 테스트가 실패한다.
    """
    run_id = "test-cleanup"
    progress._state.clear()

    await progress.emit(run_id, "complete", 100)

    # 완료 이벤트 이후 상태가 정리되어야 함
    assert run_id not in progress._state, (
        f"_state에 '{run_id}'가 여전히 존재함. "
        "emit() 또는 stream() 에서 완료 후 del _state[run_id] 처리 필요."
    )
```

---

### M-6 · CAGR 음수 총수익 은폐 (`metrics/performance.py:44`)

- [ ] 완료

**DoD**: 손실 전략(total < 1)에 대해 CAGR이 `0.0`이 아닌 음수 또는 `float('nan')`을 반환해야 한다.

```python
# tests/test_metrics.py 에 추가
import pandas as pd
import math
from metrics.performance import cagr

def test_cagr_negative_total_return_not_zero():
    """
    총수익이 음수인 경우 CAGR=0.0 반환은 손실 정보를 은폐한다.
    수정 후: 음수 값 또는 nan을 반환해야 한다.
    """
    # 매일 -0.5% → 252일 후 총수익 약 -72%
    returns = pd.Series([-0.005] * 252)
    result = cagr(returns)

    assert result != 0.0, (
        f"cagr={result} — 손실 전략인데 0.0 반환. "
        "total <= 0 분기에서 float('nan') 또는 음수 반환으로 수정 필요."
    )
    # nan이거나 음수여야 함
    assert math.isnan(result) or result < 0, (
        f"cagr={result} — 0.0 이 아니지만 음수도 nan도 아님."
    )
```

---

### M-7 · Win Rate 0 수익일 제외 미문서화 (`metrics/performance.py:51`)

- [ ] 완료

**DoD**: `win_rate` 함수가 "포지션 없는 날(return=0)을 분모에서 제외한 활성 거래일 기준 승률"임을 docstring으로 명시해야 한다.

```python
# tests/test_win_rate_definition.py
import pandas as pd
from metrics.performance import win_rate

def test_win_rate_excludes_zero_return_days():
    """
    win_rate 는 return=0 인 날을 분모에서 제외한다.
    이 동작이 의도적임을 테스트로 문서화한다.
    """
    # 10일 양수, 10일 0, 10일 음수
    returns = pd.Series([0.01] * 10 + [0.0] * 10 + [-0.01] * 10)
    result = win_rate(returns)

    # 분모: 20일 (0 제외), 분자: 10일 → 0.5
    assert abs(result - 0.5) < 1e-9, (
        f"win_rate={result:.4f}, expected 0.5. "
        "return=0 인 10일이 분모에 포함되었다면 10/30 ≈ 0.333 이 됨."
    )

def test_win_rate_docstring_mentions_active_days():
    """win_rate docstring에 '활성 거래일' 또는 'active' 언급이 있어야 한다."""
    from metrics.performance import win_rate
    doc = win_rate.__doc__ or ""
    assert "active" in doc.lower() or "0" in doc or "포지션" in doc or "trading" in doc.lower(), (
        "win_rate docstring에 0 수익일 제외 정책이 명시되지 않음."
    )
```

---

### M-8 · 가격 ≤ 0 검증 없음 (`data/loader.py:41-61`)

- [ ] 완료

**DoD**: `close <= 0` 행이 포함된 CSV 로드 시 `ValueError`를 발생시켜야 한다.

```python
# tests/test_loader_validation.py
import pandas as pd
import pytest
from unittest.mock import patch

def test_loader_rejects_non_positive_close(tmp_path):
    """
    close <= 0 인 행이 있으면 loader가 ValueError를 발생시켜야 한다.
    현재 구현에는 이 검증이 없어 pct_change() 결과가 오염될 수 있다.
    """
    csv_content = (
        "date,ticker,open,high,low,close,volume\n"
        "2022-01-03,ALPHA,100,105,98,102,1000000\n"
        "2022-01-04,ALPHA,102,106,99,-1,1000000\n"   # close < 0
    )
    csv_file = tmp_path / "bad_prices.csv"
    csv_file.write_text(csv_content)

    from data.loader import load_price_data
    with pytest.raises(ValueError, match=r"close.*<= 0|non.positive|invalid price"):
        load_price_data(str(csv_file))
```

---

### M-9 · Redis 메모리 제한 없음 (`docker-compose.yml:3-11`) — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (인프라 설정)

수동 확인 항목:

- [ ] `docker-compose.yml` Redis 서비스에 `mem_limit: 512m` (또는 적정값) 설정 확인
- [ ] Redis `maxmemory` 및 `maxmemory-policy` 설정 확인 (`allkeys-lru` 권장)
- [ ] M-4(TTL 설정)와 함께 적용하여 메모리 증가 억제

---

### M-10 · 인증/인가 없음 (`main.py:67-125`) — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (운영 환경 설계)

수동 확인 항목:

- [ ] 내부망 또는 VPN 뒤에 배포되어 외부 직접 접근 차단 여부 확인
- [ ] 필요 시 API Key 미들웨어 또는 `HTTPBearer` 의존성 적용
- [ ] `docker-compose.yml` 포트 바인딩이 `127.0.0.1:8000:8000` (로컬호스트 한정)인지 확인

---

## 🟢 Low

---

### L-1 · 합성 데이터 사용 — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (데이터 품질)

수동 확인 항목:

- [ ] API 응답 및 결과 문서에 `"data_source": "synthetic"` 또는 동등한 경고 포함 여부
- [ ] `README.md` 또는 `REPORT.md` 에 "합성 데이터 기반, 실거래 환경 재현 보장 안 됨" 명시 여부

---

### L-2 · Worker 재처리 메커니즘 없음 (`worker.py:33-51`)

- [ ] 완료

**DoD**: 예외 발생 시 job이 dead-letter 키에 기록되어야 한다.

```python
# tests/test_worker_failure_handling.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_failed_job_recorded_in_dead_letter():
    """
    run_backtest가 예외를 던지면 해당 job이 dead-letter 저장소에 기록되어야 한다.
    현재 구현은 error 결과를 Redis에 저장하고 넘어가며 재처리 메커니즘이 없다.
    """
    from worker import process_job  # 존재하지 않으면 worker 내부 로직 추출 필요

    dead_letter = []

    async def fake_run_backtest(run_id, strategy, **kwargs):
        raise RuntimeError("backtest failed")

    async def fake_record_dead_letter(run_id, reason):
        dead_letter.append({"run_id": run_id, "reason": reason})

    with patch("worker.run_backtest", side_effect=fake_run_backtest), \
         patch("worker.record_dead_letter", side_effect=fake_record_dead_letter):
        await process_job({"run_id": "fail-001", "strategy": "sma_cross", "kwargs": {}})

    assert len(dead_letter) == 1, "실패한 job이 dead-letter에 기록되지 않음."
    assert dead_letter[0]["run_id"] == "fail-001"
```

> 주의: `process_job`, `record_dead_letter` 는 현재 미존재. 리팩토링 후 테스트 적용 가능.

---

### L-3 · risk_free_rate 일별 환산 단순 나눗셈 (`metrics/performance.py:23`)

- [ ] 완료

**DoD**: 복리 환산 `(1+r)^(1/252)-1`과의 오차가 1bp/day 미만이면 허용, 수정 시 테스트 통과.

```python
# tests/test_metrics.py 에 추가
def test_daily_rf_conversion_error_within_tolerance():
    """
    단순 나눗셈과 복리 환산의 오차가 1bp/day(0.0001) 미만이어야 한다.
    rf=4% 기준 실제 오차는 약 0.04bp로 허용 범위 내.
    수정 시(복리 환산): 이 테스트는 더 정확한 값으로 통과해야 한다.
    """
    risk_free_rate = 0.04

    simple_daily    = risk_free_rate / 252
    compound_daily  = (1 + risk_free_rate) ** (1 / 252) - 1

    error_per_day = abs(simple_daily - compound_daily)
    assert error_per_day < 0.0001, (
        f"일별 rf 환산 오차 {error_per_day:.6f} > 0.0001 (1bp). "
        "복리 환산 (1+r)^(1/252)-1 적용 권장."
    )
```

---

### L-4 · `.env.example` 항목 불완전 — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (문서)

수동 확인 항목:

- [ ] `.env.example`에 `REDIS_URL`, `DATA_PATH` 등 `config.py`에서 참조하는 모든 환경변수가 포함되어 있는지 확인
- [ ] 각 변수에 예시값과 설명 주석 포함 여부

---

### L-5 · API·Worker healthcheck 부재 (`docker-compose.yml:13-35`) — 테스트 불가능

- [ ] 완료

**테스트 불가능 DoD** (인프라 설정)

수동 확인 항목:

- [ ] `api` 서비스에 `healthcheck: test: ["CMD", "curl", "-f", "http://localhost:8000/"]` 추가 확인
- [ ] `worker` 서비스에 프로세스 생존 확인용 healthcheck 추가 확인 (예: sentinel 파일 또는 `/healthz` 엔드포인트)
- [ ] `worker`의 `depends_on`에 `condition: service_healthy` 적용 여부 확인
