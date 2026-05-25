#!/usr/bin/env python3
"""Resolve NotebookLM notebook reuse decisions from a local topic registry."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


class RegistryError(ValueError):
    """Raised when a registry cannot produce a safe routing decision."""


DRIVE_FILE_RE = re.compile(r"/file/d/([^/]+)")
DEFAULT_REGISTRY = Path("config/notebooks.local.json")
EXAMPLE_REGISTRY = Path("config/notebooks.example.json")


def extract_drive_file_id(value: str) -> str:
    """Return a Drive file id from either a full Drive URL or a raw id."""
    match = DRIVE_FILE_RE.search(value)
    if match:
        return match.group(1)
    return value.strip()


def load_registry(path: str | Path) -> Dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def default_registry_path() -> Path:
    if DEFAULT_REGISTRY.exists():
        return DEFAULT_REGISTRY
    return EXAMPLE_REGISTRY


def resolve_notebook(
    registry: Mapping[str, Any],
    drive_url_or_file_id: str,
    title: str = "",
    explicit_topic: Optional[str] = None,
) -> Dict[str, Any]:
    drive_file_id = extract_drive_file_id(drive_url_or_file_id)
    topic = _find_topic(registry.get("topics", []), explicit_topic, title)
    extraction_mode = _extraction_mode(registry)

    if explicit_topic and topic is None:
        raise RegistryError(f"Unknown topic: {explicit_topic}")

    if topic is None:
        return _single_source_decision(drive_file_id, title, extraction_mode)

    existing_source = _find_source(topic.get("sources", []), drive_file_id)
    decision = {
        "drive_file_id": drive_file_id,
        "topic_id": topic["id"],
        "topic_label": topic.get("label", topic["id"]),
        "notebook_id": topic.get("notebook_id"),
        "notebook_title": topic.get("notebook_title") or f"Wiki Topic: {topic.get('label', topic['id'])}",
        "notebook_action": "reuse_topic_notebook",
        "source_action": "skip_existing_source" if existing_source else "add_source",
        "existing_source_id": existing_source.get("source_id") if existing_source else None,
        "query_scope": "target_source_only",
        "extraction_mode": extraction_mode,
        "routing_reason": _routing_reason(topic, explicit_topic, title),
    }
    decision.update(_extraction_actions(extraction_mode, topic_matched=True))
    return decision


def _single_source_decision(
    drive_file_id: str,
    title: str,
    extraction_mode: str = "single_source_first",
) -> Dict[str, Any]:
    notebook_title = f"Wiki: {title.strip()}" if title.strip() else f"Wiki: {drive_file_id}"
    return {
        "drive_file_id": drive_file_id,
        "topic_id": None,
        "topic_label": None,
        "notebook_id": None,
        "notebook_title": notebook_title,
        "notebook_action": "create_single_source_notebook",
        "source_action": "add_source",
        "existing_source_id": None,
        "query_scope": "target_source_only",
        "extraction_mode": extraction_mode,
        "extraction_notebook_action": "create_single_source_notebook",
        "topic_notebook_action": "none",
        "routing_reason": "default_policy:single_source_notebook",
    }


def build_targeted_query_prompt(
    title: str,
    drive_file_id: str,
    source_id: Optional[str] = None,
    topic_id: Optional[str] = None,
) -> str:
    source_line = f"source_id: {source_id}" if source_id else "source_id: newly_added_source"
    topic_line = f"topic_id: {topic_id}" if topic_id else "topic_id: single-source"
    return f"""다음 문서를 분석해줘.

분석 범위:
- primary_scope: 대상 PDF만
- title: {title}
- drive_file_id: {drive_file_id}
- {source_line}
- {topic_line}
- source_scoped_query: 가능하면 NotebookLM query에서 이 source_id만 대상으로 지정해
- topic_notebook_context: 같은 NotebookLM 노트북의 다른 PDF는 비교/연결 섹션에서만 참고

중요한 제한:
- 핵심 개념, 핵심 주장, 주요 수치, 실무 시사점은 대상 PDF에 근거해서만 작성해.
- 같은 topic notebook에 있는 다른 PDF의 내용을 대상 PDF의 내용처럼 쓰지 마.
- 다른 PDF에서 온 정보는 반드시 "비교/연결 섹션"에만 분리해서 적어.
- 대상 PDF에서 확인되지 않는 내용은 "대상 PDF 근거 없음"으로 표시해.

출력 형식:

## 핵심 개념
- 대상 PDF에서 정의하거나 반복적으로 사용하는 주요 개념과 용어 (3~7개)

## 핵심 주장 / 요점
- 대상 PDF의 핵심 내용과 결론 (5~10개 bullet)

## 주요 수치 / 기준
- 대상 PDF에 언급된 구체적인 수치, 비율, 기준

## 관련 주제
- 대상 PDF와 연결되는 개념, 법령, 기준서 목록 (Obsidian wikilink 형식)

## 실무 시사점
- 감사 또는 업무에서 이 대상 PDF를 활용할 때 주의할 점

## 비교/연결 섹션
- 같은 topic notebook의 다른 PDF와 연결되는 부분
- 다른 PDF에서 온 내용은 대상 PDF 근거와 분리해서 표시

## 근거 한계
- 대상 PDF만으로 확인되지 않는 사항
"""


def _find_topic(
    topics: Iterable[Mapping[str, Any]],
    explicit_topic: Optional[str],
    title: str,
) -> Optional[Mapping[str, Any]]:
    topic_list = list(topics)
    if explicit_topic:
        return next((topic for topic in topic_list if topic.get("id") == explicit_topic), None)

    title_text = title.casefold()
    for topic in topic_list:
        for keyword in topic.get("routing_keywords", []):
            if str(keyword).casefold() in title_text:
                return topic
    return None


def _find_source(
    sources: Iterable[Mapping[str, Any]],
    drive_file_id: str,
) -> Optional[Mapping[str, Any]]:
    return next(
        (source for source in sources if source.get("drive_file_id") == drive_file_id),
        None,
    )


def _routing_reason(
    topic: Mapping[str, Any],
    explicit_topic: Optional[str],
    title: str,
) -> str:
    if explicit_topic:
        return f"explicit_topic:{explicit_topic}"

    title_text = title.casefold()
    for keyword in topic.get("routing_keywords", []):
        if str(keyword).casefold() in title_text:
            return f"keyword:{keyword}"
    return "topic_selected"


def _extraction_mode(registry: Mapping[str, Any]) -> str:
    mode = registry.get("default_extraction_mode", "source_scoped_topic_query")
    allowed = {"single_source_first", "source_scoped_topic_query"}
    if mode not in allowed:
        raise RegistryError(f"Unknown extraction mode: {mode}")
    return str(mode)


def _extraction_actions(extraction_mode: str, topic_matched: bool) -> Dict[str, str]:
    if not topic_matched:
        return {
            "extraction_notebook_action": "create_single_source_notebook",
            "topic_notebook_action": "none",
        }
    if extraction_mode == "source_scoped_topic_query":
        return {
            "extraction_notebook_action": "reuse_topic_notebook",
            "topic_notebook_action": "query_target_source_in_topic",
        }
    return {
        "extraction_notebook_action": "create_single_source_notebook",
        "topic_notebook_action": "add_source_after_extraction",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve whether a Drive PDF should reuse a topic NotebookLM notebook."
    )
    parser.add_argument("drive_url_or_file_id")
    parser.add_argument("--registry", default=str(default_registry_path()))
    parser.add_argument("--title", default="")
    parser.add_argument("--topic")
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    decision = resolve_notebook(
        load_registry(args.registry),
        args.drive_url_or_file_id,
        title=args.title,
        explicit_topic=args.topic,
    )
    if args.print_prompt:
        print(
            build_targeted_query_prompt(
                title=args.title,
                drive_file_id=decision["drive_file_id"],
                source_id=decision["existing_source_id"],
                topic_id=decision["topic_id"],
            )
        )
    else:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
