---
name: audit-data
description: |
  퀀트 리서치 또는 ML 파이프라인 코드베이스의 데이터 로딩·검증·캐싱 레이어의
  무결성 문제를 탐지.
  NaN 처리, 날짜 정렬, 캐시 안전성, 입력 검증, 종목 선택 편향,
  수정주가 일관성을 동적 탐색으로 점검한다.
  사용 시점: "데이터 파이프라인 감사", "data integrity check", "NaN 처리 검사",
  "캐시 안전성 점검", "데이터 로딩 오류 확인"이라고 요청할 때.
---

# Data Pipeline Integrity Audit

데이터 로딩, 검증, 캐싱 레이어의 무결성 문제를 탐지합니다.

## Codebase Discovery

점검 전, 다음 grep/glob으로 관련 파일을 찾아 역할을 바인딩하라.

1. **데이터 로더** — `pd.read_csv(|pd.read_parquet(|yfinance|alpaca|ccxt` 포함 파일; `REQUIRED_COLUMNS|required_columns` 패턴도 검색
2. **캐시 모듈** — 모듈 레벨 `_cache.*=.*\{\}|lru_cache|functools.cache`; TTL/invalidation 패턴(`time.time()|ttl|expire`) 유무 확인
3. **유니버스 모듈** — `def get_universe|def eligible_tickers|def tradeable` 포함 파일; `as_of` 파라미터 유무 확인
4. **실제 컬럼명 확정** — 로더 파일 읽기: close/price/adj_close, return/daily_return 등 실제 사용 컬럼명 추출
5. **NaN/정렬 처리 위치** — 로더에서 `fillna(|dropna(|sort_values(|sort_index(` 호출 위치 파악
6. **샘플 데이터** — `data/`, `tests/`, `fixtures/`의 CSV/parquet 파일 첫 20행 읽기

## 체크리스트

### 1. NaN / 결측 처리
- Discovery Step 5에서 찾은 `fillna(0)` 위치와 의미 확인:
  - Discovery Step 4에서 추출한 수익률 컬럼(daily_return 등) 각 ticker 첫 행의 NaN → 0 처리는 적절한가
  - 중간에 빈 날짜(거래 중단, 상장폐지)가 있으면 어떻게 처리되는가
  - 0으로 채운 수익이 Sharpe/CAGR 계산에 미치는 영향

### 2. 날짜 정렬 보장
- Discovery Step 1 로더에서 MultiIndex 변환 전 정렬 순서 확인
- `sort_values` 후 `sort_index` 등 두 번 정렬이 일관적인지 확인
- ticker별 날짜 수가 다를 때 (상장일이 다른 경우) ticker 슬라이싱 결과가 올바른지

### 3. 캐시 안전성
- Discovery Step 2에서 찾은 캐시 모듈 확인:
  - 여러 worker 프로세스에서 각자 캐시를 가짐 → 메모리 낭비 가능성
  - 소스 파일이 갱신되어도 캐시 무효화 메커니즘 없음 → stale data 위험
  - 캐시 크기 제한 없음 → 대용량 데이터 시 OOM 가능성

### 4. 입력 검증
- Discovery Step 1에서 찾은 `REQUIRED_COLUMNS` 체크 외에 추가 검증 여부:
  - Discovery Step 4의 가격 컬럼(close 등)에 <= 0인 행 처리
  - 미래 날짜 데이터 포함 여부 체크
  - 중복 (date, ticker) 쌍 처리

### 5. Universe 필터링
- Discovery Step 3에서 찾은 유니버스 모듈이 어떤 기준으로 ticker를 포함/제외하는지 확인
- 데이터 불완전한 ticker(날짜 수 적은 것)가 포함되면 백테스트 편향 발생 가능

### 6. 수정주가(Adjusted Price) 여부
- Discovery Step 6의 샘플 데이터와 Step 4의 실제 컬럼명으로 close 컬럼이 주식 분할(Stock Split) 및 배당(Dividend) 조정된 값인지 확인
- 조정되지 않은 경우: 주식 분할 시점에 close가 급락하고 수익률이 비정상적으로 음수로 계산되어 백테스트 신뢰도 손상
- 확인 방법: 데이터 생성 스크립트가 있으면 읽어 시뮬레이션 데이터 생성 여부 확인
  - 시뮬레이션 데이터라면: 분할/배당 이벤트가 없으므로 **해당 없음**으로 명시하고 종료
  - 실제 시장 데이터라면: 데이터 출처(Yahoo Finance `Adj Close`, Bloomberg Adjusted 등) 명시 여부 확인

## 샘플 데이터 확인

Discovery Step 6에서 찾은 샘플 데이터 첫 20행을 읽고:
- 실제 컬럼 구조 확인
- NaN/이상값 존재 여부
- 날짜 범위와 ticker 수

---

## 출력 형식

아래 형식으로 결과를 작성한 뒤, `reports/audit-data.md` 파일로 저장하세요.

---

## audit-data 결과 — {오늘 날짜}

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
