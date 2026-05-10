# NotebookLM Wiki Pipeline

Drive에 있는 대용량 PDF를 Claude Code 컨텍스트에 직접 넣지 않고, NotebookLM이 먼저 읽게 한 뒤 결과만 받아 Obsidian Wiki 노트로 정리하는 토큰 절감 파이프라인입니다.

설치 후 Claude Code에서 한 줄로 실행합니다.

```
/pdf-to-wiki https://drive.google.com/file/d/YOUR_FILE_ID
```

---

## 왜 필요한가

AI 코딩 도구의 성능이 좋아질수록 병목은 모델 지능보다 컨텍스트 관리와 토큰 비용이 됩니다. 특히 PDF, 보고서, 기준서, 매뉴얼처럼 긴 문서를 다룰 때는 원문 전체를 넣는 방식이 빠르게 한계에 부딪힙니다.

예를 들어 100페이지 PDF를 Drive MCP로 직접 읽으면 수만 토큰이 Claude 컨텍스트를 지나갑니다. 반면 이 파이프라인에서는 Claude Code가 PDF 본문을 직접 읽지 않습니다. Drive URL만 NotebookLM에 넘기고, NotebookLM이 내부에서 문서를 처리합니다. Claude Code는 NotebookLM의 분석 결과, 보통 수백~수천 토큰만 받아서 노트를 만듭니다.

| 방식 | Claude 컨텍스트에 들어오는 것 | 비용 |
|------|-------------------------------|------|
| PDF 직접 로드 | PDF 전체 텍스트 | 긴 문서일수록 토큰 급증 |
| NotebookLM 경유 | Drive URL + 분석 결과 텍스트 | 원문 독해 비용을 NotebookLM으로 이동 |

## 대상 사용자

- 긴 PDF를 AI에게 자주 읽히지만 토큰 비용과 컨텍스트 오염이 부담스러운 사람
- Google Drive, NotebookLM, Obsidian을 이미 업무 흐름에 쓰는 사람
- "대충 요약"이 아니라 나중에 다시 찾을 수 있는 개인 Wiki 노트를 만들고 싶은 사람
- Claude Code 같은 에이전트형 도구를 문서 처리 파이프라인의 조립자로 쓰고 싶은 사람

## 아키텍처

```text
Google Drive PDF
  |
  | source_add(drive_url)          ← URL만 전달. PDF 본문은 Claude 컨텍스트 비통과.
  v
NotebookLM (내부 처리)
  |
  | notebook_query(분석 프롬프트)
  v
분석 결과 텍스트 (500~2,000 토큰)
  |
  | Claude Code — Markdown 구조화 + [[wikilink]] 보강
  v
{your-obsidian-vault}/AI_Generated/{title}.md
```

---

## 전제 조건

| 항목 | 설명 |
|------|------|
| Claude Code | claude.ai 계정 필요. Pro 이상 권장 (MCP 통합 지원) |
| Google Drive 연결 | claude.ai → Settings → Integrations → Google Drive에서 OAuth 연결. **API 키 불필요.** |
| NotebookLM 계정 | Google 계정으로 로그인. Free tier 사용 가능 (쿼리 ~50회/일 제한) |
| Obsidian Vault | 로컬 Vault 디렉토리 경로 확인 필요 |
| `uv` | Python 툴 설치 관리자. `brew install uv` 또는 [공식 설치](https://docs.astral.sh/uv/getting-started/installation/) |

## 설치

**1. Google Drive를 claude.ai에 연결**

별도 API 키 없이 OAuth로 연결합니다.

```
claude.ai → Settings → Integrations → Google Drive → Connect
```

연결 후 Claude Code 세션에서 Google Drive MCP 도구가 자동으로 활성화됩니다.

**2. `notebooklm-mcp-cli` 설치**

```bash
uv tool install notebooklm-mcp-cli
```

**3. NotebookLM 로그인**

```bash
nlm login
```

브라우저가 열리며 Google 계정으로 인증합니다. 쿠키 기반이며 2~4주마다 재인증이 필요합니다.

**4. Claude Code에 MCP 서버 등록**

```bash
nlm setup add claude-code
```

**5. `/pdf-to-wiki` 슬래시 커맨드 등록**

이 레포의 `commands/pdf-to-wiki.md`를 Claude Code 커맨드 디렉토리에 복사합니다.

```bash
cp commands/pdf-to-wiki.md ~/.claude/commands/pdf-to-wiki.md
```

Claude Code 세션을 재시작하면 `/pdf-to-wiki`가 슬래시 커맨드로 자동 노출됩니다.

**6. 출력 디렉토리 준비**

생성된 노트가 저장될 디렉토리를 만듭니다. 본인 Obsidian vault 경로에 맞게 조정하세요.

```bash
mkdir -p ~/your-obsidian-vault/AI_Generated
```

> `commands/pdf-to-wiki.md` 안의 저장 경로(`~/vault/00_Wiki/AI_Generated/`)도 본인 경로로 수정하세요.

---

## 사용법

### 기본 실행

Claude Code 세션에서 Drive URL 또는 파일 ID를 넘깁니다.

```
/pdf-to-wiki https://drive.google.com/file/d/YOUR_FILE_ID
```

제목을 직접 지정하려면 두 번째 인자를 추가합니다.

```
/pdf-to-wiki https://drive.google.com/file/d/YOUR_FILE_ID K-IFRS 1109 금융상품
```

### 실행 순서 (자동)

`/pdf-to-wiki`를 실행하면 Claude Code가 다음 단계를 자동으로 처리합니다.

1. Drive 파일 메타데이터 확인 (파일명, URL)
2. NotebookLM 노트북 생성
3. Drive PDF를 NotebookLM 소스로 추가 (30~60초 처리 대기)
4. 구조화 분석 쿼리 전송
5. 분석 결과를 Obsidian 노트로 변환 + `[[wikilink]]` 보강
6. `AI_Generated/` 디렉토리에 저장
7. 완료 보고 (저장 경로, NotebookLM 노트북 ID, 절감 토큰 추정)

### 출력 노트 형식

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

{NotebookLM 분석 결과}

---
*이 노트는 /pdf-to-wiki 커맨드로 자동 생성됨. 원본 PDF: [{파일명}]({drive_url})*
```

---

## 인증 관리

NotebookLM 쿠키는 2~4주마다 만료됩니다. 인증 오류 발생 시:

```bash
nlm login
```

Free tier에서는 쿼리가 ~50회/일로 제한됩니다. 대량 처리 중 실패 시 인증 문제인지 일일 한도 초과인지 먼저 구분하세요.

---

## 사용 사례

**기준서·규정 정리** — K-IFRS, 감사기준, 법령처럼 길고 반복적으로 참조되는 PDF를 Wiki 노트로 변환합니다.

**리서치 PDF 요약** — 논문, 리포트, 산업 분석 자료를 핵심 개념과 시사점 중심으로 정리합니다.

**지식 베이스 구축** — 프로젝트마다 흩어진 PDF를 Obsidian의 연결형 Wiki로 축적합니다.

**코딩 세션 맥락 재사용** — 한 번 정리한 노트를 이후 Claude Code 세션의 짧은 컨텍스트로 재사용합니다. 매번 PDF 전체를 다시 넣지 않아도 됩니다.

---

## 주의사항

**하지 말아야 할 것:**

- Drive MCP로 PDF 본문 전체 다운로드 (`download_file_content` 사용 금지)
- 로컬에서 PDF 텍스트 추출 후 프롬프트에 붙여넣기
- 서로 무관한 여러 PDF를 하나의 NotebookLM 노트북에 혼합

**올바른 방식:**

- Drive MCP는 파일명·URL 확인에만 사용
- PDF 1개 = NotebookLM 노트북 1개
- NotebookLM source에는 Drive URL 또는 파일 ID만 전달

---

## 실패 대응

| 오류 | 원인 | 해결 |
|------|------|------|
| 인증 오류 | NotebookLM 쿠키 만료 | `nlm login` 재실행 후 세션 재시작 |
| source 처리 지연 | NotebookLM PDF 처리 시간 | 1분 대기 후 source 상태 재확인 |
| Drive 접근 오류 | PDF 공유 권한 없음 | Drive 파일 공유 설정 확인 |
| 쿼리 한도 초과 | Free tier ~50회/일 제한 | 다음 날 재시도 또는 처리량 축소 |
| 답변이 너무 일반적 | 프롬프트 맥락 부족 | "감사 실무자 관점에서", "K-IFRS 기준으로" 등 맥락 명시 |

---

## 프로젝트 구성

```text
.
├── commands/
│   └── pdf-to-wiki.md      ← /pdf-to-wiki 슬래시 커맨드 (설치 시 ~/.claude/commands/ 에 복사)
└── docs/
    └── adr/
        └── 0001-notebooklm-mcp-approach.md   ← NotebookLM vs Gemini API 선택 근거
```

## 설계 결정

NotebookLM MCP 방식을 채택한 이유는 `docs/adr/0001-notebooklm-mcp-approach.md`에 정리되어 있습니다.

- Gemini API는 공식적이고 안정적이지만 별도 API 키와 구현이 필요합니다.
- NotebookLM MCP는 비공식 내부 API 기반이라 깨질 수 있지만, 설정이 간단하고 NotebookLM의 문서 처리 경험을 그대로 활용할 수 있습니다.
- 이 파이프라인은 운영 시스템이라기보다 개인 지식 관리 도구이므로, 현재는 실용성이 우선입니다.

## 로드맵

- [ ] 여러 PDF 일괄 처리 플로우
- [ ] 생성 노트의 wikilink 후보 자동 점검
- [ ] NotebookLM 노트북 재사용 정책
- [ ] 샘플 입력/출력 노트 추가
