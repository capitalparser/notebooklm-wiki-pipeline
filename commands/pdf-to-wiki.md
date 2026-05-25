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
/pdf-to-wiki <drive_url_or_file_id> [wiki_title] [--topic topic_id]
```

- `drive_url_or_file_id`: Google Drive 파일 URL 또는 파일 ID
- `wiki_title` (선택): 생성할 Wiki 노트 제목. 생략 시 파일명에서 추론.
- `--topic` (선택): `config/notebooks.example.json` 형식의 registry에 있는 주제 ID. 지정하면 해당 NotebookLM 노트북을 재사용한다.

## Notebook 재사용 정책

기본 정책은 여전히 안전한 `single_source_notebook`이다. 주제가 불명확하거나 registry에 없는 자료는 새 NotebookLM 노트북을 만든다.

주제별 Notebook 재사용은 아래 조건에서만 수행한다.

- 사용자가 `--topic`을 명시했거나, 제목이 registry의 `routing_keywords`와 매칭됨
- 해당 topic의 NotebookLM 노트북이 문서 세트 관점에서 좁게 정의되어 있음
- 같은 Drive file ID가 이미 `sources`에 있으면 source를 다시 추가하지 않고 기존 source를 재사용함

재사용의 이점:

- 같은 주제의 기존 PDF와 신규 PDF를 한 노트북에서 비교할 수 있음
- 기존 기준서, 리포트, 메모와 연결되는 개념을 NotebookLM이 더 잘 찾을 수 있음
- topic-level 질문에서는 누적 문서 세트 전체를 대상으로 답변을 받을 수 있음

단, 신규 PDF 노트를 만들 때는 답변 오염을 막아야 한다. 같은 NotebookLM 노트북에 있는 이전 PDF까지 섞여 답변될 수 있으므로, 기본 `notebook_query`는 MCP 인자의 `source_ids=[target_source_id]`로 대상 PDF source만 지정한다. 프롬프트에서도 대상 PDF만 primary scope로 제한하고, 기존 PDF는 `비교/연결 섹션`에서만 참고하게 한다.

기본 추출 모드는 `source_scoped_topic_query`다.

- 대상 PDF를 topic notebook에 추가하거나 이미 등록된 source를 찾는다.
- 신규 Wiki 노트용 `notebook_query`는 topic notebook에서 실행하되 MCP 인자 `source_ids=[target_source_id]`를 전달하고, 프롬프트에도 target `source_id` 또는 `drive_file_id`를 명시한다.
- 기존 topic source는 비교/연결 섹션에서만 사용한다.
- MCP schema가 특정 source 지정 query를 지원하지 않거나 불명확할 때만 `single_source_first`를 fallback으로 사용한다.

라우팅 결정은 로컬 helper로 먼저 확인할 수 있다.

```bash
python3 scripts/notebook_registry.py \
  "https://drive.google.com/file/d/YOUR_FILE_ID/view" \
  --title "K-IFRS 1109 금융상품" \
  --topic audit-accounting \
  --registry config/notebooks.local.json
```

## 실행 절차

아래 단계를 순서대로 실행한다. notebooklm-mcp 서버가 활성화되어 있어야 한다.
인증 오류 발생 시: `nlm login` 실행 후 재시도.

### Step 1 — Drive 파일 메타데이터 확인

`mcp__claude_ai_Google_Drive__get_file_metadata` 또는 `mcp__claude_ai_Google_Drive__search_files`로
파일명, Drive URL, Drive file ID를 확인한다. 파일 내용은 읽지 않는다.

### Step 2 — NotebookLM 노트북 결정

`--topic`이 있거나 제목으로 주제를 추론할 수 있으면 registry를 기준으로 NotebookLM 노트북 재사용 여부를 결정한다.

```bash
python3 scripts/notebook_registry.py "{drive_url_or_file_id}" --title "{wiki_title}" --topic "{topic_id}"
```

결정값 해석:

- `reuse_topic_notebook`: 기존 topic NotebookLM 노트북 사용
- `create_single_source_notebook`: 새 단일 PDF용 NotebookLM 노트북 생성
- `skip_existing_source`: 같은 Drive file ID가 이미 등록되어 있으므로 source 추가 생략
- `add_source`: Step 3에서 NotebookLM source 추가 필요
- `source_scoped_topic_query`: topic notebook 안에서 target source를 지정해 분석
- `single_source_first`: source 지정 query가 불명확할 때 대상 PDF 전용 extraction notebook에서 분석

registry가 없거나 topic을 확정할 수 없으면 새 노트북을 만든다.

`create_single_source_notebook`인 경우 `notebook_create` 도구로 새 노트북 생성:
- 제목: `Wiki: {wiki_title}` (예: `Wiki: K-IFRS 1109 금융상품`)

`reuse_topic_notebook`인 경우 registry의 `notebook_id`를 사용한다.

### Step 3 — Topic notebook에 Drive PDF 추가

`source_scoped_topic_query`에서는 대상 PDF를 topic notebook에 추가한 뒤, 생성된 source ID를 target으로 삼는다.
Step 2의 `source_action`이 `skip_existing_source`이면 기존 `source_id`를 target으로 사용한다.

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

### Step 4 — 대상 PDF 한정 구조화 분석 쿼리

`notebook_query` 도구를 호출할 때는 프롬프트만으로 제한하지 말고, MCP 인자의 `source_ids`에도 target source ID를 넣는다.

```text
notebook_query(
  notebook_id="{topic_notebook_id}",
  source_ids=["{target_source_id}"],
  query="{아래 프롬프트}"
)
```

아래 프롬프트 실행:

```
다음 문서를 분석해줘.

분석 범위:
- primary_scope: 대상 PDF만
- title: {wiki_title}
- drive_file_id: {drive_file_id}
- source_id: {source_id 또는 newly_added_source}
- topic_id: {topic_id 또는 single-source}
- source_scoped_query: 가능하면 NotebookLM query에서 이 source_id만 대상으로 지정해
- topic_notebook_context: 같은 NotebookLM 노트북의 다른 PDF는 비교/연결 섹션에서만 참고

중요한 제한:
- 핵심 개념, 핵심 주장, 주요 수치, 실무 시사점은 대상 PDF에 근거해서만 작성해.
- 같은 topic notebook에 있는 다른 PDF의 내용을 대상 PDF의 내용처럼 쓰지 마.
- 다른 PDF에서 온 정보는 반드시 "비교/연결 섹션"에만 분리해서 적어.
- 대상 PDF에서 확인되지 않는 내용은 "대상 PDF 근거 없음"으로 표시해.

## 핵심 개념
- 대상 PDF에서 정의하거나 반복적으로 사용하는 주요 개념과 용어 (3~7개)

## 핵심 주장 / 요점
- 대상 PDF의 핵심 내용과 결론 (5~10개 bullet)

## 주요 수치 / 기준
- 대상 PDF에 언급된 구체적인 수치, 비율, 기준

## 관련 주제
- 대상 PDF와 연결되는 개념, 법령, 기준서 목록 (Obsidian wikilink 형식으로)
  예: [[K-IFRS 1109]], [[금융상품 분류]], [[상각후원가]]

## 실무 시사점
- 감사 또는 업무에서 이 대상 PDF를 활용할 때 주의할 점

## 비교/연결 섹션
- 같은 topic notebook의 다른 PDF와 연결되는 부분
- 다른 PDF에서 온 내용은 대상 PDF 근거와 분리해서 표시

## 근거 한계
- 대상 PDF만으로 확인되지 않는 사항
```

### Step 5 — Registry 갱신 안내

새로 추가한 source가 있으면 완료 보고에 registry 갱신값을 표시한다.

- `drive_file_id`
- NotebookLM `source_id`
- title
- added_at

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
drive_file_id: {drive_file_id}
notebook_id: {notebook_id}
notebook_policy: {reuse_topic_notebook | create_single_source_notebook}
extraction_mode: {single_source_first | source_scoped_topic_query}
query_scope: target_source_only
topic: {topic_id | null}
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
- NotebookLM 노트북 ID
- target source ID
- NotebookLM 응답의 `sources_used`
- Notebook 정책 (`reuse_topic_notebook` 또는 `create_single_source_notebook`)
- extraction mode (`source_scoped_topic_query` 또는 fallback `single_source_first`)
- source 처리 (`add_source` 또는 `skip_existing_source`)
- 발견된 [[wikilink]] 개수
- 소요 토큰 추정 (Drive 직접 읽기 대비 절감 효과)

## 오류 처리

- **인증 오류**: `nlm login` 실행 안내
- **소스 처리 실패**: 1분 후 재시도, 3회 실패 시 수동 확인 안내
- **Free tier 한도 초과**: 50 queries/day 한도. 다음 날 재시도 안내
- **파일 접근 불가**: Drive 공유 설정 확인 안내
