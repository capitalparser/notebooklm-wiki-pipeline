# CONTEXT — 도메인 사전

## 핵심 개념

**토큰 외주화 (Token Offloading)**
대용량 문서를 Claude 컨텍스트에 직접 로드하지 않고, 외부 시스템(NotebookLM)이 처리하게 한 뒤 결과 텍스트만 수령하는 패턴. 본 파이프라인의 핵심 설계 원칙.

**NotebookLM MCP**
`notebooklm-mcp-cli` PyPI 패키지가 제공하는 MCP 서버. 비공식 내부 API 역방향 엔지니어링 기반.
Claude Code가 `notebooklm-mcp` 서버를 통해 NotebookLM 노트북을 도구로 직접 호출.

**notebook_query 결과**
NotebookLM이 생성한 답변 텍스트. 전체 PDF가 아닌 요약/분석 텍스트만 Claude 컨텍스트에 진입.
분량: 보통 500~2000 토큰 (PDF 100페이지 → 직접 로드 시 ~50,000 토큰 대비).

**Drive 소스 추가 (source_add)**
Drive 파일 URL/ID를 NotebookLM에 전달. NotebookLM이 자체적으로 Drive에서 파일을 가져옴.
Claude에는 URL 문자열(수십 토큰)만 전달 — 파일 내용 비통과.

**Obsidian 노트 (출력 형식)**
`[[wikilink]]` 포함 마크다운 파일. `~/vault/00_Wiki/AI_Generated/` 저장.
기존 Wiki 페이지와 연결되도록 Claude가 wikilink를 추가.

## 금지 패턴

- `mcp__claude_ai_Google_Drive__download_file_content` — 토큰 낭비 원인, 사용 금지
- NotebookLM 노트북 1개에 무관한 PDF 혼재 — 노트북은 PDF 1개당 1개 원칙

## 관련 MCP 서버

| 서버 | 용도 |
|------|------|
| `notebooklm-mcp` | PDF 처리 외주화 (핵심) |
| `mcp__claude_ai_Google_Drive__*` | 파일 ID/URL 조회만 |
