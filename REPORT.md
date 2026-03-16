# REPORT — alpha-pipeline 감사 결과

> ⚠️ **경고**: 이 파이프라인은 합성(synthetic) 데이터를 사용합니다. 실제 시장 데이터가 아닙니다. 백테스트 결과를 실제 투자 판단에 사용하지 마십시오.

> 감사 일자: 2026-03-16
> 감사 범위: bias / concurrency / data / metrics / production 5개 영역
> 결론: **현재 상태에서 백테스트 결과를 신뢰할 수 없음**

---

## 1. 전체 요약

| 심각도 | 건수 |
|--------|------|
| 🔴 Critical | 6 |
| 🟠 High | 9 |
| 🟡 Medium | 10 |
| 🟢 Low | 5 |
| **합계** | **30** |

---

## 2. 발견 항목 전체 목록

### 🔴 Critical

| # | 항목 | 파일:라인 | 문제 요약 |
|---|------|----------|----------|
| C-1 | SMA Cross 룩어헤드 편향 | `strategy/sma_cross.py:41` | `signal * daily_return` — `shift(1)` 누락으로 당일 시그널로 당일 수익 계산. MACD·RSI는 올바르게 적용되어 있어 SMA만 누락 |
| C-2 | Sharpe Ratio 연환산 계수 누락 | `metrics/performance.py:29` | `excess.mean() / excess.std()` — `* sqrt(252)` 없어 연간 Sharpe 대비 약 1/15.87 수준으로 과소 보고. `test_metrics.py:32`가 이 버그를 감지하도록 설계되었으며 현재 **실패** 상태 |
| C-3 | Universe Survivorship Bias | `data/universe.py:28-31` | `as_of` 파라미터를 받지만 항상 `last_date` 기준으로 스냅샷. GAMMA 같은 중도 상장폐지 종목이 전체 기간에서 제외됨. `test_backtest.py:55` 현재 **실패** 상태 |
| C-4 | 전략 인스턴스 캐시 kwargs 무시 | `strategy/registry.py:26-28` | 캐시 키가 `name`만 — 파라미터를 바꿔 같은 전략을 호출해도 첫 번째 인스턴스를 반환. 파라미터 변경이 결과에 반영되지 않는 silent failure |
| C-5 | `_ticker_returns` 전역 가변 리스트 | `runner/backtest.py:23,43,56` | 모듈 레벨 `global` 리스트를 run마다 재사용. `asyncio.gather` 동시 실행 시 여러 run의 ticker 수익이 섞여 portfolio 계산 오염 |
| C-6 | SSE 공유 `_cursor` 크로스토킹 | `runner/progress.py:19,27,42` | 단일 전역 문자열 `_cursor`를 모든 run_id가 덮어씀. run-A 구독 클라이언트가 run-B의 이벤트를 수신 |

---

### 🟠 High

| # | 항목 | 파일:라인 | 문제 요약 |
|---|------|----------|----------|
| H-1 | MACD signal 기본값 오타 | `strategy/macd.py:22` | `signal: int = settings.MACD_SLOW`(26) — `settings.MACD_SIGNAL`(9)이어야 함. signal과 slow가 동일 span이 되어 교차 신호 거의 미발생 |
| H-2 | `emit()` await 누락 | `runner/backtest.py:77` | `emit(run_id, "complete", 100)` — `await` 없어 코루틴 객체만 생성되고 실행 안 됨. SSE 클라이언트가 180초 타임아웃까지 대기 |
| H-3 | 동시 비교 실행 시 전역 상태 충돌 | `runner/dispatcher.py:27-34` | `asyncio.gather`로 여러 `run_backtest`를 병렬 실행 — C-5·C-6을 동시에 트리거. `/api/compare` 호출 시 결과 오염 확정 |
| H-4 | GAMMA 상장폐지 ticker 0 패딩 편향 | `runner/backtest.py:72` | `fillna(0)`으로 GAMMA 데이터 없는 기간을 0 수익으로 채움. Sharpe·CAGR·MDD 전반에 편향 주입 |
| H-5 | 캐시 무효화 메커니즘 없음 | `data/cache.py:12` | 모듈 레벨 `_cache`에 TTL·mtime 체크·크기 제한 없음. CSV 갱신 후 재시작 전까지 stale data 반환 |
| H-6 | `/api/backtest` macd·rsi kwargs 누락 | `main.py:88-91` | `strategy == "sma_cross"`일 때만 kwargs 구성 — macd·rsi는 항상 `{}`로 전달, 전략별 파라미터 설정 불가 |
| H-7 | `/api/compare` kwargs 전 전략 일괄 적용 | `main.py:124-125` | `short_window`·`long_window`를 macd·rsi에도 전달. 각 전략이 다른 파라미터 이름을 기대하여 키가 무시되거나 TypeError 발생 가능 |
| H-8 | Worker restart 정책 없음 | `docker-compose.yml:32` | `restart: "no"` — 워커 크래시 시 자동 재시작 안 됨. 큐에 적재된 모든 작업이 처리 중단 |
| H-9 | lookahead 테스트 임계값 과도하게 느슨 | `tests/test_signals.py:56-64` | `assert sharpe > -5.0` — 테스트 내 주석에 "threshold is intentionally too loose"로 명시. C-1 SMA lookahead 버그가 존재해도 CI에서 통과 |

---

### 🟡 Medium

| # | 항목 | 파일:라인 | 문제 요약 |
|---|------|----------|----------|
| M-1 | Train/Test 분리 없음 (In-Sample 성과) | `runner/backtest.py` 전체 | walk-forward·hold-out 분리 없이 전체 데이터로 단일 백테스트. 보고된 수치는 모두 in-sample 성과 |
| M-2 | 다중 전략 비교 시 다중검정 조정 없음 | `runner/dispatcher.py:27-34` | 3개 전략 병렬 실행 후 best-pick. 5% 유의수준 기준 실제 유형 I 오류율 최대 14%로 상승 |
| M-3 | SMA 거래비용 계산 타이밍 불일치 | `strategy/sma_cross.py:38-41` | turnover 산정 기준 날짜와 strategy_return 적용 날짜 불일치. C-1 수정 시 함께 재산정 필요 |
| M-4 | Redis 결과 TTL 미설정 | `storage/result_store.py:39` | `client.set(...)` — `ex=` 없어 결과가 Redis에 영구 누적. 장시간 운영 시 메모리 선형 증가 |
| M-5 | SSE 상태 정리 미구현 | `runner/progress.py:17,31-51` | run 완료 후 `_state[run_id]` 삭제 코드 없음. 완료된 모든 run의 상태가 API 프로세스 메모리에 누적 |
| M-6 | CAGR 음수 총수익 은폐 | `metrics/performance.py:44` | `total <= 0`이면 0.0 반환. 큰 손실 전략도 CAGR = 0으로 표시되어 실제 손실 정보 손실 |
| M-7 | Win Rate 0 수익일 제외 미문서화 | `metrics/performance.py:51` | `returns != 0` 필터로 포지션 없는 날을 분모에서 제외하는 특수 정의이나 미문서화 |
| M-8 | 가격 ≤ 0 검증 없음 | `data/loader.py:41-61` | `close <= 0` 행 필터링 없음. 실데이터 전환 시 `pct_change()` 결과 오염 가능 |
| M-9 | Redis 메모리 제한 없음 | `docker-compose.yml:3-11` | Redis 컨테이너에 `mem_limit` 미설정. 결과·큐 누적 시 OOM으로 호스트 메모리 고갈 가능 |
| M-10 | 인증/인가 없음 | `main.py:67-125` | 모든 엔드포인트 인증 미적용. 내부 연구 시스템이라도 네트워크 접근 제어 없을 경우 무제한 접근 가능 |

---

### 🟢 Low

| # | 항목 | 파일:라인 | 문제 요약 |
|---|------|----------|----------|
| L-1 | 합성 데이터 사용 (실데이터 아님) | `scripts/generate_data.py` 전체 | Gaussian random walk 기반 합성 데이터. 팻테일·변동성 군집·유동성 제한 등 실제 시장 특성 미반영 |
| L-2 | Worker 재처리 메커니즘 없음 | `worker.py:33-51` | 실패한 job을 Dead Letter Queue에 보내거나 재시도하는 로직 없음 |
| L-3 | risk_free_rate 일별 환산 단순 나눗셈 | `metrics/performance.py:23` | `/ 252` 사용; 이론적 복리 환산 `(1+r)^(1/252)-1` 대비 약 0.4bp/day 오차. 실용 범위 내이나 기록 |
| L-4 | `.env.example` 항목 불완전 | `.env.example:1-7` | `REDIS_URL` 등 인프라 관련 환경변수 누락 |
| L-5 | API·Worker healthcheck 부재 | `docker-compose.yml:13-35` | `api`·`worker` 서비스에 healthcheck 미설정. `depends_on`이 서비스 준비 여부를 보장 못함 |

---

## 3. 고친 것 / 고치지 않은 것

### 고치지 않은 것 — 전체 항목 미수정

이번 감사는 **발견 및 문서화** 단계이며, 코드 수정은 진행하지 않았다.
아래는 우선순위 판단과 수정 권고 순서이다.

### 수정 우선순위 판단

**즉시 수정 (결과를 신뢰하기 위한 최소 조건)**

| 순위 | 항목 | 이유 |
|------|------|------|
| 1 | C-2 Sharpe 연환산 누락 | 모든 전략의 핵심 지표가 15배 과소 보고. 기존 테스트(test_metrics.py:32)가 실패 상태로 버그 확인 완료. 단 1줄 수정 |
| 2 | C-1 SMA lookahead bias | 성과 과장의 직접 원인. `shift(1)` 1줄 추가. 동시에 M-3 비용 타이밍도 정합성 맞춰야 함 |
| 3 | C-3 Universe survivorship bias | `as_of` 파라미터 실제 적용. 기존 테스트(test_backtest.py:55)가 실패 상태로 수정 방향 명확 |
| 4 | C-4 캐시 kwargs 무시 | 파라미터 변경이 결과에 반영 안 되는 근본 원인. 캐시 키를 `(name, frozenset(kwargs.items()))`로 변경 |
| 5 | C-5 + C-6 전역 상태 동시성 버그 | `/api/compare` 사용 시 결과 오염 확정. `_ticker_returns`를 함수 로컬로, `_cursor`를 run_id별로 격리 |

**단기 수정 (운영 안정성)**

- H-1: MACD 기본값 오타 — 1줄 수정
- H-2: `await emit(...)` — 1줄 수정
- H-6, H-7: API kwargs 디스패치 수정
- H-8: `docker-compose.yml` restart 정책 변경

**중기 검토 (연구 품질)**

- H-4: 상장폐지 ticker 가중치 동적 조정
- M-1: walk-forward 또는 hold-out 분리 추가
- M-2: 다중검정 조정 또는 결과 보고 시 명시
- M-4, M-5: Redis TTL 및 SSE 상태 정리

**보류 가능 (현재 범위 내 허용)**

- L-1: 합성 데이터 — 내부 연구 목적임을 명시하는 것으로 대체 가능
- M-10: 인증 — 네트워크 레벨 접근 제어로 대체 가능

---

## 4. 신뢰 가능 여부

**현재 상태: 신뢰 불가**

다음 세 가지 구조적 결함이 동시에 존재한다:

1. **수치 자체가 틀렸다** — Sharpe Ratio가 실제값의 6.3%로 보고(C-2)되며, SMA Cross는 룩어헤드 편향으로 성과가 과장(C-1)된다.
2. **유니버스 구성이 잘못됐다** — Survivorship Bias로 인해 비교 대상 자체가 실제와 다르다(C-3).
3. **파라미터가 반영 안 된다** — 인스턴스 캐시가 kwargs를 무시하여 파라미터를 바꿔도 같은 결과가 나온다(C-4).

이 네 가지 Critical 버그(C-1~C-4)가 수정되기 전까지 출력된 Sharpe·CAGR·MDD 수치를 절대값 또는 전략 간 비교 용도로 신뢰해서는 안 된다.

**신뢰 가능 조건 (최소)**

- [ ] C-1 SMA shift(1) 적용
- [ ] C-2 Sharpe `* sqrt(252)` 적용
- [ ] C-3 `as_of` 파라미터 실제 사용
- [ ] C-4 캐시 키에 kwargs 포함
- [ ] C-5·C-6 전역 상태 격리 (동시 실행 시)
- [ ] 위 수정 후 기존 실패 테스트(test_metrics.py, test_backtest.py) 통과 확인
