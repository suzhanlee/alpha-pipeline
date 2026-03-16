# Alpha Pipeline

알파 리서치 팀 내부 백테스팅 파이프라인입니다.
데이터 로딩 → 전략 시그널 생성 → 백테스트 실행 → 성과 지표 계산을 담당합니다.
실제 집행(execution)이나 포지션 관리는 포함하지 않습니다.

---

## 아키텍처

이 파이프라인은 세 개의 서비스로 구성된 분산 시스템입니다.

```
┌─────────────┐     HTTP      ┌─────────────┐
│   Client    │ ──────────── │   api       │  FastAPI (port 8000)
└─────────────┘               └──────┬──────┘
                                     │ LPUSH (job)
                               ┌─────▼──────┐
                               │   redis    │  Redis 7 (port 6379)
                               └─────┬──────┘
                                     │ RPOP (job)
                               ┌─────▼──────┐
                               │   worker   │  async worker
                               └─────────────┘
```

- **api**: HTTP 요청 수신, 작업 큐 투입, SSE 스트리밍, 결과 조회
- **worker**: 큐에서 작업을 꺼내 백테스트 실행, 결과를 Redis에 저장
- **redis**: 작업 큐 (`jobs`) + 결과 저장소 (`result:{run_id}`)

---

## 셋업

### Docker Compose (권장)

```bash
# 전체 스택 기동
docker compose up --build

# 백그라운드 실행
docker compose up --build -d
```

서버가 뜨면 `http://localhost:8000/docs` 에서 API 스펙을 확인할 수 있습니다.

### 로컬 실행 (Redis 별도 필요)

> **주의**: 로컬 실행은 api와 worker가 동일 프로세스 메모리를 공유하지 않습니다.
> 일부 동작은 Docker Compose 환경에서만 재현됩니다.

```bash
# 1. 의존성 설치
uv sync

# 2. 샘플 데이터 생성
uv run python scripts/generate_data.py

# 3. Redis 실행 (별도 터미널 또는 Docker)
docker run -p 6379:6379 redis:7-alpine

# 4. Worker 실행 (별도 터미널)
uv run python worker.py

# 5. API 서버 실행
uv run uvicorn main:app --reload
```

---

## 테스트

```bash
uv run pytest -v
```

---

## 빠른 확인

```bash
# 백테스트 시작
curl -s -X POST http://localhost:8000/api/backtest \
  -H "Content-Type: application/json" \
  -d '{"strategy": "sma_cross"}' | python3 -m json.tool

# 결과 조회 (run_id는 위 응답에서 확인)
curl -s http://localhost:8000/api/result/{run_id} | python3 -m json.tool

# 전략 비교
curl -s -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"strategies": ["sma_cross", "macd"]}' | python3 -m json.tool

# SSE 진행률 스트림
curl -N http://localhost:8000/api/progress/{run_id}

# 동시 실행
bash scripts/run_concurrent.sh
```

---

## 구조

```
├── main.py               API 서버 (FastAPI)
├── worker.py             백테스트 워커
├── config.py             설정
├── docker-compose.yml    서비스 오케스트레이션
├── Dockerfile.api        API 컨테이너 이미지
├── Dockerfile.worker     Worker 컨테이너 이미지
├── data/
│   ├── loader.py         가격 데이터 로더
│   ├── universe.py       종목 유니버스
│   ├── cache.py          인프로세스 캐시
│   └── sample_data.csv   합성 시세 데이터
├── strategy/
│   ├── base.py           전략 기반 클래스
│   ├── sma_cross.py      SMA 크로스오버
│   ├── macd.py           MACD
│   ├── rsi.py            RSI
│   └── registry.py       전략 레지스트리
├── metrics/
│   └── performance.py    성과 지표 계산
├── runner/
│   ├── backtest.py       백테스트 실행기
│   ├── progress.py       SSE 진행률 스트림
│   ├── dispatcher.py     멀티 전략 비교 디스패처
│   └── job_queue.py      인프로세스 작업 큐
├── mq/
│   └── redis_queue.py    Redis 기반 작업 큐
├── storage/
│   └── result_store.py   Redis 기반 결과 저장소
├── tests/
└── scripts/
    ├── generate_data.py
    └── run_concurrent.sh
```
