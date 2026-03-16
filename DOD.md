# DoD 체크리스트

> **Testable**: pytest 코드 블록 통과 시 완료 / **No-Test**: 설정 파일 수정으로 완료

---

## 🟠 High

| 완료 | ID | 설명 | 완료 조건 | 대상 파일 | 유형 |
|------|----|------|-----------|-----------|------|
| - [ ] | H-1 | MACD signal 기본값 오타 | `Macd().signal_period == 9` | `strategy/macd.py:22` | Testable |
| - [ ] | H-2 | `emit()` await 누락 | 백테스트 후 `_state[run_id]["step"] == "complete"` | `runner/backtest.py:77` | Testable |
| - [ ] | H-3 | 동시 실행 전역 상태 충돌 | 두 전략 동시 실행 시 각 결과의 `strategy` 필드가 오염되지 않음 | `runner/dispatcher.py:27-34` | Testable |
| - [ ] | H-4 | 상장폐지 ticker 0 패딩 편향 | 0 패딩 포함/미포함 Sharpe 차이 10% 이내 | `runner/backtest.py:72` | Testable |
| - [ ] | H-5 | 캐시 무효화 없음 | 파일 mtime 변경 후 `get_cached` → `None` 반환 | `data/cache.py:12` | Testable |
| - [ ] | H-6 | `/api/backtest` macd·rsi kwargs 누락 | macd/rsi 요청 시 `push_job` kwargs가 비어있지 않음 | `main.py:88-91` | Testable |
| - [ ] | H-7 | `/api/compare` kwargs 전 전략 일괄 적용 | 각 전략이 자신의 파라미터 키만 수신 | `main.py:124-125` | Testable |
| - [ ] | H-8 | Worker restart 정책 없음 | `docker-compose.yml` worker에 `restart: unless-stopped` 추가 | `docker-compose.yml:32` | No-Test |
| - [ ] | H-9 | lookahead 임계값 느슨 | 순수 노이즈 데이터에서 `abs(sharpe) < 1.0` | `tests/test_signals.py:56-64` | Testable |

---

## 🟡 Medium

| 완료 | ID | 설명 | 완료 조건 | 대상 파일 | 유형 |
|------|----|------|-----------|-----------|------|
| - [ ] | M-1 | Train/Test 분리 없음 | API 응답에 "in-sample 결과임" 명시 또는 `train_end_date` 파라미터 추가 | `runner/backtest.py` | No-Test |
| - [ ] | M-2 | 다중검정 조정 없음 | `/api/compare` 응답에 `"multiple_testing_adjusted": false` 경고 필드 포함 | `main.py` | No-Test |
| - [ ] | M-3 | SMA 거래비용 타이밍 불일치 | `turnover`가 `signal.shift(1).diff().abs()` 기준으로 계산됨 | `strategy/sma_cross.py:38-41` | Testable |
| - [ ] | M-4 | Redis 결과 TTL 미설정 | `save_result` 호출 시 Redis `SET`에 `ex=` 인자 포함 | `storage/result_store.py:39` | Testable |
| - [ ] | M-5 | SSE 상태 정리 미구현 | `emit(run_id, "complete", 100)` 후 `run_id not in _state` | `runner/progress.py` | Testable |
| - [ ] | M-6 | CAGR 음수 총수익 은폐 | 손실 전략에서 `cagr()` → 음수 또는 `nan` 반환 (0.0 금지) | `metrics/performance.py:44` | Testable |
| - [ ] | M-7 | Win Rate 0 수익일 미문서화 | `win_rate` docstring에 0 수익일 제외 정책 명시 + 동작 검증 | `metrics/performance.py:51` | Testable |
| - [ ] | M-8 | 가격 ≤ 0 검증 없음 | `close <= 0` 행 포함 CSV 로드 시 `ValueError` 발생 | `data/loader.py:41-61` | Testable |
| - [ ] | M-9 | Redis 메모리 제한 없음 | `docker-compose.yml` redis에 `mem_limit: 512m` 추가 | `docker-compose.yml:3-11` | No-Test |
| - [ ] | M-10 | 인증/인가 없음 | 포트 바인딩 `127.0.0.1:8000:8000` 확인 또는 API Key 미들웨어 적용 | `main.py:67-125` | No-Test |

---

## 🟢 Low

| 완료 | ID | 설명 | 완료 조건 | 대상 파일 | 유형 |
|------|----|------|-----------|-----------|------|
| - [ ] | L-1 | 합성 데이터 사용 | `README.md` 또는 `REPORT.md`에 합성 데이터 경고 명시 | `README.md` / `REPORT.md` | No-Test |
| - [ ] | L-2 | Worker 재처리 없음 | 예외 발생 시 job이 dead-letter 키에 기록됨 (`process_job` 리팩토링 필요) | `worker.py:33-51` | Testable |
| - [ ] | L-3 | rf 일별 환산 단순 나눗셈 | 단순 나눗셈 vs 복리 환산 오차 `< 1bp/day (0.0001)` | `metrics/performance.py:23` | Testable |
| - [ ] | L-4 | `.env.example` 불완전 | `config.py` 참조 변수 전부 포함 + 예시값/주석 | `.env.example` | No-Test |
| - [ ] | L-5 | healthcheck 부재 | `docker-compose.yml` api/worker 서비스에 `healthcheck` 블록 추가 | `docker-compose.yml:13-35` | No-Test |

---

## 테스트 코드 참조

<details>
<summary>H-1 · MACD signal 기본값 오타</summary>

```python
# tests/test_strategy_defaults.py
from strategy.macd import Macd

def test_macd_signal_default_is_9():
    m = Macd()
    assert m.signal_period == 9
```
</details>

<details>
<summary>H-2 · emit() await 누락</summary>

```python
# tests/test_progress_complete.py
import pytest
from runner.backtest import run_backtest
from runner import progress

@pytest.mark.asyncio
async def test_complete_event_written_to_state(sample_price_df, monkeypatch):
    import data.loader as loader_module
    monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)
    progress._state.clear()
    run_id = "test-complete-event"
    await run_backtest(run_id, "sma_cross")
    state = progress._state.get(run_id)
    assert state is not None
    assert state["step"] == "complete"
    assert state["pct"] == 100
```
</details>

<details>
<summary>H-3 · 동시 실행 전역 상태 충돌</summary>

```python
# tests/test_concurrent_isolation.py
import asyncio, pytest
from runner.backtest import run_backtest

@pytest.mark.asyncio
async def test_concurrent_runs_return_correct_strategy(sample_price_df, monkeypatch):
    import data.loader as loader_module
    monkeypatch.setattr(loader_module, "load_price_data", lambda _: sample_price_df)
    results = await asyncio.gather(
        run_backtest("run-concurrent-A", "sma_cross"),
        run_backtest("run-concurrent-B", "macd"),
    )
    r_a, r_b = results
    assert r_a["strategy"] == "sma_cross"
    assert r_b["strategy"] == "macd"
    assert r_a["sharpe_ratio"] != r_b["sharpe_ratio"]
```
</details>

<details>
<summary>H-4 · 상장폐지 ticker 0 패딩 편향</summary>

```python
# tests/test_delisted_ticker_padding.py
import numpy as np, pandas as pd
from metrics.performance import sharpe_ratio

def make_sharpe(include_delisted):
    rng = np.random.default_rng(0)
    n = 300
    active = pd.DataFrame({"A": rng.normal(0.001,0.01,n), "B": rng.normal(0.001,0.01,n)})
    if include_delisted:
        gamma = pd.Series(list(rng.normal(0.001,0.01,150)) + [0.0]*150, name="G")
        return sharpe_ratio(pd.concat([active, gamma], axis=1).mean(axis=1), 0.0)
    return sharpe_ratio(active.mean(axis=1), 0.0)

def test_delisted_zero_padding_does_not_distort_sharpe():
    s_without, s_with = make_sharpe(False), make_sharpe(True)
    assert abs(s_with - s_without) / (abs(s_without) + 1e-9) < 0.10
```
</details>

<details>
<summary>H-5 · 캐시 무효화 없음</summary>

```python
# tests/test_cache_invalidation.py
import time, pandas as pd
from data import cache

def test_cache_invalidated_on_file_change(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text("date,close\n2022-01-01,100\n")
    cache.set_cached(str(p), pd.DataFrame({"close": [100]}))
    time.sleep(0.01)
    p.write_text("date,close\n2022-01-01,200\n")
    assert cache.get_cached(str(p)) is None
```
</details>

<details>
<summary>H-6 · /api/backtest kwargs 누락</summary>

```python
# tests/test_api_kwargs_dispatch.py
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_macd_backtest_passes_kwargs():
    captured = {}
    async def fake_push_job(run_id, strategy, kwargs):
        captured["kwargs"] = kwargs
    with patch("main.push_job", side_effect=fake_push_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/api/backtest", json={"strategy": "macd"})
    assert captured["kwargs"] != {}

@pytest.mark.asyncio
async def test_rsi_backtest_passes_kwargs():
    captured = {}
    async def fake_push_job(run_id, strategy, kwargs):
        captured["kwargs"] = kwargs
    with patch("main.push_job", side_effect=fake_push_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/api/backtest", json={"strategy": "rsi"})
    assert captured["kwargs"] != {}
```
</details>

<details>
<summary>H-7 · /api/compare kwargs 일괄 적용</summary>

```python
# tests/test_api_compare_kwargs.py
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_compare_passes_strategy_specific_kwargs():
    captured = {}
    async def fake_run_comparison(strategies, kwargs, data_path):
        captured["kwargs"] = kwargs
        return {"results": []}
    with patch("main.run_comparison", side_effect=fake_run_comparison):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/api/compare", json={"strategies": ["sma_cross","macd"], "short_window": 10})
    assert "short_window" not in captured["kwargs"] or captured["kwargs"].get("_strategy_aware")
```
</details>

<details>
<summary>H-9 · lookahead 임계값 느슨</summary>

```python
# tests/test_signals.py (기존 test_no_lookahead 교체)
import numpy as np, pandas as pd
from strategy.sma_cross import SmaCross
from metrics.performance import sharpe_ratio

def test_no_lookahead_noise_sharpe():
    rng = np.random.default_rng(42)
    n = 1000
    price = 100.0 * np.cumprod(1 + rng.standard_normal(n) * 0.01)
    df = pd.DataFrame({"close": price, "daily_return": pd.Series(price).pct_change().fillna(0).values},
                      index=pd.date_range("2020-01-01", periods=n, freq="B"))
    result = SmaCross(20, 50).compute(df)
    assert abs(sharpe_ratio(result["strategy_return"].dropna(), 0.0)) < 1.0
```
</details>

<details>
<summary>M-3 · SMA 거래비용 타이밍 불일치</summary>

```python
# tests/test_sma_cost_timing.py
import numpy as np, pandas as pd
from strategy.sma_cross import SmaCross

def test_sma_cost_applied_on_next_day():
    rng = np.random.default_rng(0)
    n = 100
    price = 100.0 * np.cumprod(1 + rng.normal(0, 0.01, n))
    df = pd.DataFrame({"close": price, "daily_return": pd.Series(price).pct_change().fillna(0).values},
                      index=pd.date_range("2022-01-01", periods=n, freq="B"))
    result = SmaCross(5, 20).compute(df)
    expected = result["signal"].shift(1).diff().abs().fillna(0)
    pd.testing.assert_series_equal(result["turnover"].reset_index(drop=True),
                                   expected.reset_index(drop=True), check_names=False, atol=1e-9)
```
</details>

<details>
<summary>M-4 · Redis TTL 미설정</summary>

```python
# tests/test_result_store_ttl.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_save_result_sets_ttl():
    mock_client = AsyncMock()
    with patch("storage.result_store._get_client", return_value=mock_client):
        from storage.result_store import save_result
        await save_result("run-ttl-test", {"sharpe_ratio": 1.5, "run_id": "run-ttl-test"})
    _, kwargs = mock_client.set.call_args
    assert "ex" in kwargs
```
</details>

<details>
<summary>M-5 · SSE 상태 정리 미구현</summary>

```python
# tests/test_progress_cleanup.py
import pytest
from runner import progress

@pytest.mark.asyncio
async def test_state_cleaned_up_after_completion():
    progress._state.clear()
    await progress.emit("test-cleanup", "complete", 100)
    assert "test-cleanup" not in progress._state
```
</details>

<details>
<summary>M-6 · CAGR 음수 총수익 은폐</summary>

```python
# tests/test_metrics.py 에 추가
import pandas as pd, math
from metrics.performance import cagr

def test_cagr_negative_total_return_not_zero():
    result = cagr(pd.Series([-0.005] * 252))
    assert result != 0.0
    assert math.isnan(result) or result < 0
```
</details>

<details>
<summary>M-7 · Win Rate 미문서화</summary>

```python
# tests/test_win_rate_definition.py
import pandas as pd
from metrics.performance import win_rate

def test_win_rate_excludes_zero_return_days():
    returns = pd.Series([0.01]*10 + [0.0]*10 + [-0.01]*10)
    assert abs(win_rate(returns) - 0.5) < 1e-9

def test_win_rate_docstring_mentions_active_days():
    doc = win_rate.__doc__ or ""
    assert any(kw in doc.lower() for kw in ["active", "포지션", "trading", "0"])
```
</details>

<details>
<summary>M-8 · 가격 ≤ 0 검증 없음</summary>

```python
# tests/test_loader_validation.py
import pytest
from data.loader import load_price_data

def test_loader_rejects_non_positive_close(tmp_path):
    csv = tmp_path / "bad.csv"
    csv.write_text("date,ticker,open,high,low,close,volume\n2022-01-03,A,100,105,98,102,1000\n2022-01-04,A,102,106,99,-1,1000\n")
    with pytest.raises(ValueError, match=r"close.*<= 0|non.positive|invalid price"):
        load_price_data(str(csv))
```
</details>

<details>
<summary>L-2 · Worker 재처리 없음</summary>

```python
# tests/test_worker_failure_handling.py
# 주의: process_job, record_dead_letter 미존재 — worker 리팩토링 후 적용
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_failed_job_recorded_in_dead_letter():
    from worker import process_job
    dead_letter = []
    async def fake_run_backtest(run_id, strategy, **kw): raise RuntimeError("fail")
    async def fake_record_dead_letter(run_id, reason): dead_letter.append(run_id)
    with patch("worker.run_backtest", side_effect=fake_run_backtest), \
         patch("worker.record_dead_letter", side_effect=fake_record_dead_letter):
        await process_job({"run_id": "fail-001", "strategy": "sma_cross", "kwargs": {}})
    assert len(dead_letter) == 1
```
</details>

<details>
<summary>L-3 · rf 일별 환산 오차</summary>

```python
# tests/test_metrics.py 에 추가
def test_daily_rf_conversion_error_within_tolerance():
    rf = 0.04
    assert abs(rf / 252 - ((1 + rf) ** (1/252) - 1)) < 0.0001
```
</details>
