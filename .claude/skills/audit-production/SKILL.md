---
name: audit-production
description: |
  비동기 Python API 서비스의 프로덕션 운영 준비 상태를 종합 점검.
  HTTP 에러 처리, 파라미터 묵인 실패, 설정/시크릿 관리, 관측가능성,
  테스트 커버리지, 컨테이너 인프라, 보안 취약점을 동적 탐색으로 검토한다.
  사용 시점: "프로덕션 감사", "production readiness audit", "배포 전 점검",
  "Docker 설정 감사", "보안 취약점 점검"이라고 요청할 때.
---

# Production Readiness Audit

프로덕션 운영 관점에서 누락된 항목을 점검합니다.

## Codebase Discovery

점검 전, 다음 grep/glob으로 관련 파일을 찾아 역할을 바인딩하라.

1. **HTTP API 진입점** — `main.py|app.py|api.py|server.py` glob; `FastAPI()|Flask(|@router.` 패턴. 모든 엔드포인트 함수와 request model 타입 목록 추출
2. **워커/백그라운드 프로세서** — `while True:` + `await` + pop 패턴(pop/RPOP/dequeue/get) 조합 파일; 또는 `asyncio.run(` 진입점
3. **설정/시크릿 모듈** — `BaseSettings|os.environ|os.getenv|dynaconf` 파일; `.env.example|.env.template` glob. 코드에서 사용된 모든 환경변수명 추출
4. **컨테이너 설정** — `Dockerfile*|docker-compose*.yml|compose.yml` glob; kubernetes/k8s/helm 디렉토리도 확인
5. **테스트 스위트** — `tests/**/*.py|test_*.py` glob; conftest.py 픽스처 패턴 확인
6. **로깅 설정** — `logging.basicConfig(|structlog|loguru|logger.exception(` 패턴
7. **파라미터 디스패치 로직** — Discovery Step 1 API 진입점에서 `if req.\w+ ==|if strategy_name ==` 패턴; kwargs 구성 조건 분기 확인

## 체크리스트

### 1. 에러 핸들링 & API 응답
- Discovery Step 1에서 찾은 각 엔드포인트에서 예외가 발생할 때 클라이언트가 받는 응답 형식 확인
- Discovery Step 2의 워커에서 백테스트 실패 시 결과가 어떻게 저장/전달되는지 확인
- 존재하지 않는 run_id로 결과 조회 시 응답 확인 (404 vs 500 vs 빈 응답)
- 잘못된 strategy_name 입력 시 에러 처리

### 2. API 파라미터 → 전략 전달 경로
- Discovery Step 7에서 찾은 파라미터 디스패치 로직 확인:
  - 전략별 분기에서 특정 전략만 kwargs를 구성하고 나머지는 `{}`로 전달되는지 확인
  - request model에 있는 파라미터가 일부 전략에서 무시되는지 확인
- 엔드포인트별로 동일한 kwargs가 전략마다 파라미터 이름이 다를 때 어떻게 처리되는지
- 이 누락이 사용자가 파라미터를 바꿔도 결과가 바뀌지 않는 silent failure를 만드는지 확인

### 3. 설정 & 시크릿 관리
- Discovery Step 3에서 찾은 설정 모듈에서 민감 정보(비밀번호 등) 처리 방식
- `.env.example`과 실제 사용되는 설정값 비교 — 빠진 항목 없는지
- 기본값이 프로덕션에 안전한지 확인 (예: DEBUG=True가 기본값이면 위험)

### 4. 관측가능성 (Observability)
- Discovery Step 6에서 찾은 로깅 설정: 수준과 구조화 여부 (JSON 로그 vs 텍스트)
- 에러 발생 시 stack trace가 로그에 남는지 확인 (`exc_info=True` 또는 `logger.exception`)
- 백테스트 완료/실패 이벤트가 기록되는지 확인
- 메트릭(요청 수, 큐 길이, 처리 시간) 수집 여부

### 5. 테스트 커버리지
- Discovery Step 5에서 찾은 테스트가 실제로 중요한 경로를 커버하는지 확인
- 각 전략의 lookahead bias를 잡아낼 수 있는 테스트 존재 여부
- 동시성 버그를 재현하는 테스트 존재 여부
- conftest.py의 fixture가 실제 데이터와 충분히 유사한지

### 6. 인프라 & 배포
- Discovery Step 4에서 찾은 컨테이너 설정에서 Redis에 메모리 제한 설정 여부
- 워커 컨테이너 재시작 정책 (`restart: unless-stopped` 등) 확인
- healthcheck 설정 여부
- API와 Worker 간 버전 불일치 가능성 (별도 배포 시)

### 7. 보안
- Discovery Step 1에서 찾은 엔드포인트에 인증/인가 없는지 확인
- `data_path` 같은 파라미터가 사용자 입력을 받는지 확인 (path traversal 위험)
- Discovery Step 4의 컨테이너 설정에서 Redis 등 내부 서비스가 외부에 포트 노출되어 있는지 확인

---

## 출력 형식

아래 형식으로 결과를 작성한 뒤, `reports/audit-production.md` 파일로 저장하세요.

---

## audit-production 결과 — {오늘 날짜}

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
