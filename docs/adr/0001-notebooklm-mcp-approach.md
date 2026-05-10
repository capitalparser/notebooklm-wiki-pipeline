# ADR-0001: NotebookLM MCP 방식 채택

Date: 2026-05-10
Status: Accepted

## Context

Drive 대용량 PDF 분석 파이프라인 구현 시 세 가지 선택지 존재:

A. Drive MCP로 PDF 직접 로드 → Claude 분석
B. Gemini API 직접 사용 (1M+ 토큰 컨텍스트)
C. notebooklm-mcp-cli 경유 NotebookLM 외주화

## Decision

**C 채택 (notebooklm-mcp-cli)**

## Rationale

- 사용자가 이미 NotebookLM을 선호하는 특정 이유 존재 (P1 전제 유지)
- MCP 패턴이 기존 인프라(Drive MCP, kreports MCP)와 일관성
- `nlm setup add claude-code` 단일 명령으로 Claude Code 통합 완료
- Python 스크립트나 추가 언어 없이 동일 세션 내 파이프라인 완결

## Trade-offs

| 항목 | 채택 (C) | 비채택 (B: Gemini API) |
|------|----------|----------------------|
| 공식성 | 비공식 역방향 API | 공식 API |
| 안정성 | NotebookLM 업데이트 시 깨질 수 있음 | 버전 보장 |
| 설치 복잡도 | `uv tool install` + `nlm login` | API 키 관리 필요 |
| 컨텍스트 절감 | ✅ Drive URL만 전달 | ✅ 동일 |
| NotebookLM 기능 | ✅ Audio, Briefing Doc 등 추가 활용 가능 | ❌ 텍스트만 |

## Consequences

- 쿠키 기반 인증으로 2-4주마다 `nlm login` 재실행 필요
- Free tier 50 queries/day 한도 → 대량 처리 시 병목
- NotebookLM 내부 API 변경 시 파이프라인 중단 가능 → 탐색 목적 범위 내 허용
