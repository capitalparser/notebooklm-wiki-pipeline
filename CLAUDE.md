# 05_notebooklm_wiki_pipeline — 프로젝트 컨텍스트

> Drive 대용량 PDF를 NotebookLM에 외주화하고, 분석 결과만 Claude Code가 수령하여
> 00_Wiki/ Obsidian 노트로 자동 변환하는 토큰-효율 파이프라인.

## 핵심 문제

Drive MCP로 PDF를 직접 읽으면 PDF 전체 텍스트가 Claude 컨텍스트를 지나가 토큰 소모가 과다.
NotebookLM이 내부에서 PDF를 처리하고 Claude는 분석 결과(텍스트)만 수령하는 구조로 해결.

## 아키텍처

```
Drive PDF (대용량)
  ↓ source_add(drive_url)  — URL만 전달, 파일 내용은 Claude 컨텍스트 비통과
NotebookLM 내부 처리
  ↓ notebook_query("분석 요청")
분석 결과 텍스트  — 수백~수천 토큰만
  ↓ Claude Code 구조화
00_Wiki/{category}/{title}.md  — [[wikilink]] 포함 Obsidian 노트
```

## 도구 구성

- **notebooklm-mcp-cli** (PyPI): `notebooklm-mcp` MCP 서버
  - 설치: `uv tool install notebooklm-mcp-cli`
  - 인증: `nlm login` (브라우저 기반 쿠키, 2-4주 유효)
  - MCP 등록: `nlm setup add claude-code`
- **Drive MCP** (`mcp__claude_ai_Google_Drive__*`): 파일 메타데이터/ID 조회용만 사용
  - `download_file_content` 사용 금지 — 토큰 낭비의 원인

## 슬래시 커맨드

- `/pdf-to-wiki` — 단일 PDF → Obsidian 노트 변환
  - 플러그인 위치: `~/.claude/commands/pdf-to-wiki.md`
  - Claude Code 세션 시작 시 자동 로드됨

## 인증 관리

NotebookLM 쿠키는 2-4주마다 만료. 만료 시:
```bash
nlm login
```
자동 갱신 시도하지만 실패 시 수동 재인증 필요.
Free tier: ~50 queries/day 한도.

## 산출물 위치

- 생성 노트: `~/vault/00_Wiki/AI_Generated/`
- 재사용 노트북: NotebookLM 웹 UI에서 확인 가능 (쿼리 기록 자동 동기화)

## ADR

- [0001-notebooklm-mcp-approach.md](docs/adr/0001-notebooklm-mcp-approach.md) — NotebookLM vs Gemini API 선택 근거
