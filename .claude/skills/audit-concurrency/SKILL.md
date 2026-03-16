---
name: audit-concurrency
description: |
  FastAPI, asyncio 워커, Redis 큐, SSE 스트림 등 분산 비동기 Python 시스템의
  동시성 버그와 async 오류를 탐지.
  글로벌 가변 상태, await 누락, 메시지 큐 원자성, 워커 루프 안정성,
  SSE 스트림 격리 문제를 동적 탐색으로 점검한다.
  사용 시점: "동시성 감사", "race condition 검사", "async 버그 확인",
  "worker 안정성 점검", "공유 상태 문제 확인"이라고 요청할 때.
---

# Concurrency & Async Audit

분산 환경에서 동시성 버그와 async 오류를 탐지합니다.

## Codebase Discovery

점검 전, 다음 grep/glob으로 관련 파일을 찾아 역할을 바인딩하라.

1. **글로벌 가변 상태** — 모든 .py에서 인덴트 0의 `^_\w+\s*=\s*[\[\{]|^_\w+:\s*(list|dict)` 패턴; `global ` 키워드를 async def 내부에서 사용하는 라인
2. **비동기 워커 루프** — `while True:` + `await` + pop 패턴(pop/RPOP/dequeue/get) 조합 파일; 또는 `asyncio.run(` 진입점
3. **메시지 큐 모듈** — `redis|aioredis|celery|rq|kafka` import + push/pop 연산 파일
4. **SSE / 스트리밍 모듈** — `AsyncGenerator|yield` in `async def|StreamingResponse|text/event-stream` 패턴
5. **인스턴스 캐시/레지스트리** — 모듈 레벨 dict + `get_\w+(name, \*\*kwargs)` 패턴
6. **HTTP API 진입점** — `FastAPI()|Flask(|@app.route|@router.` 파일

## 체크리스트

### 1. 글로벌 가변 상태 (Global Mutable State)
Discovery Step 1에서 발견된 모듈 레벨 가변 변수를 모두 탐지하고 각각 동시 실행 시 어떤 문제가 생기는지 확인:
- 리스트/딕셔너리 형태의 모듈 레벨 변수가 여러 코루틴에서 동시에 쓰이는지 확인
- SSE/진행률 모듈의 공유 커서/상태 변수 — 모든 run_id가 단일 변수를 공유하면 run-A의 이벤트가 run-B 구독자에게 전달됨
- Discovery Step 5의 인스턴스 캐시 — `get_strategy(name, **kwargs)` 류 함수가 kwargs를 무시하고 첫 번째 인스턴스를 재사용하는지 확인 (예: 다른 파라미터로 요청해도 동일 인스턴스 반환)
- 동시에 두 백테스트 실행 시 위 변수들이 서로 덮어쓰이는 구체적인 시나리오 서술

### 2. await 누락
- Discovery Step 2, 6 파일의 `async def` 함수 내에서 코루틴을 `await` 없이 호출하는 패턴 탐지
- `emit(...)` 같은 async 함수가 fire-and-forget으로 쓰이는 곳 확인
- 영향: 어떤 이벤트/결과가 실제로 전송/저장되지 않는지 추적

### 3. Redis 작업 원자성
- Discovery Step 3의 메시지 큐 모듈에서 read-modify-write 패턴 확인
- 여러 worker가 동시에 같은 job을 pop하는 가능성 확인 (Redis RPOP은 atomic이지만 로직 레벨에서 추가 처리가 있으면 문제)
- TTL/만료 설정 여부 확인

### 4. Worker 루프 안정성
- Discovery Step 2에서 찾은 워커 루프에서 예외 발생 시 worker가 죽는지 재시작하는지 확인
- 처리 중 실패한 job의 재처리 메커니즘 존재 여부

### 5. SSE Progress 격리
- Discovery Step 4에서 찾은 스트리밍 모듈의 `stream(run_id)` 류 함수가 공유 상태를 그대로 yield하는지 확인:
  - 공유 변수에 담긴 run_id를 검증하지 않고 yield하면 다른 run의 이벤트가 섞임
  - 올바른 구현: `_state[run_id]`에서 직접 해당 run 상태를 읽어 yield
- 완료된 run의 상태 항목이 정리되는지 확인 (장시간 운영 시 메모리 누수)
- SSE 클라이언트 연결 끊김 시 스트림 제너레이터가 중단되는지 확인

---

## 출력 형식

아래 형식으로 결과를 작성한 뒤, `reports/audit-concurrency.md` 파일로 저장하세요.

---

## audit-concurrency 결과 — {오늘 날짜}

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
