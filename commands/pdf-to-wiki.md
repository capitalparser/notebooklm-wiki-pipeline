# /pdf-to-wiki

Drive에 있는 대용량 PDF를 NotebookLM에 외주화하여 분석하고,
결과를 `OUTPUT_DIR`에 Obsidian 노트로 저장한다.

기본 출력 경로:

```text
OUTPUT_DIR=~/vault/00_Wiki/AI_Generated
```

설치 후 위 경로를 본인 Obsidian vault의 저장 위치로 바꿔라.

**중요**: PDF 파일 내용을 직접 읽지 않는다. Drive URL만 NotebookLM에 전달한다.
`mcp__claude_ai_Google_Drive__download_file_content` 호출 금지.

## 사용법

```
/pdf-to-wiki <drive_url_or_file_id> [wiki_title]
```

- `drive_url_or_file_id`: Google Drive 파일 URL 또는 파일 ID
- `wiki_title` (선택): 생성할 Wiki 노트 제목. 생략 시 파일명에서 추론.

## 실행 절차

아래 단계를 순서대로 실행한다. notebooklm-mcp 서버가 활성화되어 있어야 한다.
인증 오류 발생 시: `nlm login` 실행 후 재시도.

### Step 1 — Drive 파일 메타데이터 확인

`mcp__claude_ai_Google_Drive__get_file_metadata` 또는 `mcp__claude_ai_Google_Drive__search_files`로
파일명, Drive URL, Drive file ID를 확인한다. 파일 내용은 읽지 않는다.

### Step 2 — NotebookLM 노트북 생성

`notebook_create` 도구로 새 노트북 생성:
- 제목: `Wiki: {wiki_title}` (예: `Wiki: K-IFRS 1109 금융상품`)

### Step 3 — Drive PDF를 소스로 추가

`source_add` 도구로 Drive URL을 NotebookLM 소스로 추가:
- `source_type`: `drive`
- `document_id`: Step 1에서 얻은 Drive file ID
- `doc_type`: `pdf`
- `wait`: `true`
- `wait_timeout`: `120.0`
- NotebookLM이 내부에서 PDF를 가져와 처리 (Claude 컨텍스트 비통과)

예상 호출 형태:

```text
source_add(
  notebook_id="{notebook_id}",
  source_type="drive",
  document_id="{drive_file_id}",
  doc_type="pdf",
  wait=True,
  wait_timeout=120.0
)
```

설치된 `notebooklm-mcp-cli` 버전에 따라 파라미터명이 다르면 현재 MCP tool schema를 우선한다.
소스 처리 완료까지 대기한다. 상태 확인이 필요하면 `source_list_drive` 또는 현재 노출된 source 조회 도구를 사용한다.

### Step 4 — 구조화 분석 쿼리

`notebook_query` 도구로 아래 프롬프트 실행:

```
다음 형식으로 이 문서를 분석해줘:

## 핵심 개념
- 문서에서 정의하는 주요 개념과 용어 (3~7개)

## 핵심 주장 / 요점
- 문서의 핵심 내용과 결론 (5~10개 bullet)

## 주요 수치 / 기준
- 언급된 구체적인 수치, 비율, 기준 (있는 경우)

## 관련 주제
- 이 문서와 연결되는 개념, 법령, 기준서 목록 (Obsidian wikilink 형식으로)
  예: [[K-IFRS 1109]], [[금융상품 분류]], [[상각후원가]]

## 실무 시사점
- 감사 또는 업무에서 이 문서를 활용할 때 주의할 점
```

### Step 5 — 기존 Wiki 페이지 연결

~/vault/00_Wiki/ 디렉토리를 확인하여 Step 4의 "관련 주제"에서 나온
[[wikilink]] 대상이 실제로 존재하는지 확인한다.
존재하지 않는 링크는 그대로 두되 (Obsidian에서 미래 노트로 처리됨),
존재하는 링크는 상대 경로가 맞는지 검토한다.

### Step 6 — Obsidian 노트 생성

아래 템플릿으로 `{OUTPUT_DIR}/{wiki_title}.md` 파일 생성:

```markdown
---
source: notebooklm
drive_url: {drive_url}
created: {YYYY-MM-DD}
tags: [ai-generated, pdf-analysis]
---

# {wiki_title}

> AI 분석 요약 (원본: Google Drive PDF)
> 생성: {YYYY-MM-DD} | 도구: NotebookLM → Claude Code

{Step 4 분석 결과 전체}

---
*이 노트는 /pdf-to-wiki 커맨드로 자동 생성됨. 원본 PDF: [{파일명}]({drive_url})*
```

### Step 7 — 완료 보고

다음 정보를 출력한다:
- 생성된 노트 경로
- NotebookLM 노트북 ID (재사용 가능)
- 발견된 [[wikilink]] 개수
- 소요 토큰 추정 (Drive 직접 읽기 대비 절감 효과)

## 오류 처리

- **인증 오류**: `nlm login` 실행 안내
- **소스 처리 실패**: 1분 후 재시도, 3회 실패 시 수동 확인 안내
- **Free tier 한도 초과**: 50 queries/day 한도. 다음 날 재시도 안내
- **파일 접근 불가**: Drive 공유 설정 확인 안내
