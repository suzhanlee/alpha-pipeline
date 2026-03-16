# Skill 완성도 체크리스트

## 1. YAML Frontmatter — 가장 중요

```yaml
---
name: kebab-case-only          # 소문자, 하이픈만, 폴더명과 일치
description: |                 # WHAT + WHEN 둘 다 필수, 1024자 이내
  [무엇을 하는지] + [언제 쓰는지 — 트리거 문구 포함]
---
```

**완료 조건:**
- [ ] `name` = kebab-case, 대문자/공백/언더스코어 없음
- [ ] `description` = "무엇" + "언제(트리거 문구)" 동시 포함
- [ ] `<` `>` XML 문자 없음
- [ ] `claude` / `anthropic` prefix 없음

---

## 2. 파일 구조

```
my-skill/          ← kebab-case
└── SKILL.md       ← 정확히 이 이름 (대소문자 구분)
```

**완료 조건:**
- [ ] 파일명 `SKILL.md` (SKILL.MD, skill.md 안 됨)
- [ ] 폴더명 kebab-case
- [ ] 폴더 안에 `README.md` 없음

---

## 3. Description 품질 — Trigger 판별 기준

| 나쁜 예 | 좋은 예 |
|---|---|
| `Helps with projects.` | `Manages Linear sprint workflows. Use when user says "plan sprint", "create tickets", or "track tasks".` |
| `Creates documentation.` | `Generates API docs from code. Use when user asks for "API documentation", "endpoint specs", or uploads .py files.` |

**완료 조건:**
- [ ] 사용자가 실제로 말할 법한 트리거 문구 2개 이상 포함
- [ ] "너무 일반적"이지 않은지 확인: Claude에게 `"When would you use [skill name]?"` 물어봐서 답변이 정확한지 검증

---

## 4. 지시문 품질

**완료 조건:**
- [ ] 각 스텝이 구체적이고 실행 가능 (모호한 "validate properly" ❌ → "이름이 비어있지 않은지 확인" ✅)
- [ ] 에러 케이스 처리 포함
- [ ] SKILL.md 본문 5,000 단어 이하 (초과 시 `references/` 로 분리)

---

## Few-shot 예시

### 예시 1 — 단순 문서 생성 Skill

```yaml
---
name: pr-description-writer
description: Generates structured pull request descriptions from git diff or
  branch summary. Use when user says "write PR description", "draft PR",
  "create pull request body", or "summarize my changes for review".
---

# PR Description Writer

## Instructions

### Step 1: Gather Context
Ask for (or read from context):
- Target branch (default: main)
- Summary of changes if not obvious from diff

### Step 2: Generate Description
Structure:
- **What changed** (1-3 bullets)
- **Why** (motivation)
- **Test plan** (checklist)

### Step 3: Validate
Before finalizing, check:
- Does it answer "what" and "why"?
- Is the test plan actionable?

## Example

User: "Write a PR description for my auth changes"
Output:
> ## Summary
> - Replaced session tokens with JWT
> - Added token refresh endpoint
>
> ## Why
> Compliance requirement for stateless auth
>
> ## Test plan
> - [ ] Login returns JWT
> - [ ] Expired token returns 401
```

---

### 예시 2 — MCP 연동 Workflow Skill

```yaml
---
name: linear-sprint-planner
description: Automates Linear sprint planning by fetching current backlog,
  analyzing team velocity, and creating prioritized sprint tasks. Use when
  user says "plan sprint", "create sprint tasks", "Linear sprint setup",
  or "organize backlog into sprint".
metadata:
  mcp-server: linear
  version: 1.0.0
---

# Linear Sprint Planner

## Instructions

### Step 1: Fetch Current State
Call MCP: `linear_get_issues(state="backlog")`
Call MCP: `linear_get_team_velocity(last_sprints=3)`

### Step 2: Prioritize
Sort by: priority > story_points (ascending) > created_at

### Step 3: Create Sprint
Call MCP: `linear_create_cycle(name, start_date, end_date)`
For each selected issue:
  Call MCP: `linear_add_issue_to_cycle(issue_id, cycle_id)`

## Error Handling
- MCP 연결 실패 → "Linear MCP가 연결되어 있는지 Settings > Extensions 확인"
- velocity 데이터 없음 → 기본값 20 story points/sprint 사용
```

---

## 최종 완료 검증 3문장

1. **Trigger 검증:** Claude에게 `"When would you use the [name] skill?"` 물어봤을 때 정확한 시나리오를 답하는가?
2. **Non-trigger 검증:** 관련 없는 질문(예: "오늘 날씨")에 skill이 로드되지 않는가?
3. **Instruction 검증:** skill 없이 같은 작업을 하는 것보다 결과가 더 일관적이고 단계가 줄었는가?
