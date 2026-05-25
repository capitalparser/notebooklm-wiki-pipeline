import json
import unittest

from scripts.notebook_registry import (
    RegistryError,
    build_targeted_query_prompt,
    extract_drive_file_id,
    resolve_notebook,
)


class NotebookRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "default_policy": "single_source_notebook",
            "default_extraction_mode": "source_scoped_topic_query",
            "topics": [
                {
                    "id": "audit-accounting",
                    "label": "Audit and Accounting",
                    "notebook_id": "nb_audit",
                    "reuse_policy": "topic",
                    "routing_keywords": ["감사", "K-IFRS", "회계"],
                    "sources": [
                        {
                            "drive_file_id": "1ExistingAuditPdf",
                            "source_id": "src_existing",
                            "title": "K-IFRS 1109",
                        }
                    ],
                },
                {
                    "id": "stablecoin",
                    "label": "Stablecoin and Payments",
                    "notebook_id": "nb_stablecoin",
                    "reuse_policy": "topic",
                    "routing_keywords": ["stablecoin", "payment", "x402"],
                    "sources": [],
                },
            ],
        }

    def test_extracts_drive_file_id_from_drive_url(self):
        file_id = extract_drive_file_id(
            "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view"
        )

        self.assertEqual(file_id, "1AbCdEfGhIjKlMnOpQrStUvWxYz")

    def test_explicit_topic_reuses_notebook_and_skips_duplicate_source(self):
        decision = resolve_notebook(
            self.registry,
            "https://drive.google.com/file/d/1ExistingAuditPdf/view",
            title="K-IFRS 1109 update",
            explicit_topic="audit-accounting",
        )

        self.assertEqual(decision["topic_id"], "audit-accounting")
        self.assertEqual(decision["notebook_id"], "nb_audit")
        self.assertEqual(decision["notebook_action"], "reuse_topic_notebook")
        self.assertEqual(decision["source_action"], "skip_existing_source")
        self.assertEqual(decision["existing_source_id"], "src_existing")

    def test_keyword_match_routes_to_topic_notebook(self):
        decision = resolve_notebook(
            self.registry,
            "1NewAuditPdf",
            title="2026 감사 기준 체크리스트",
        )

        self.assertEqual(decision["topic_id"], "audit-accounting")
        self.assertEqual(decision["notebook_id"], "nb_audit")
        self.assertEqual(decision["source_action"], "add_source")
        self.assertEqual(decision["routing_reason"], "keyword:감사")
        self.assertEqual(decision["query_scope"], "target_source_only")
        self.assertEqual(decision["extraction_mode"], "source_scoped_topic_query")
        self.assertEqual(decision["extraction_notebook_action"], "reuse_topic_notebook")
        self.assertEqual(decision["topic_notebook_action"], "query_target_source_in_topic")

    def test_registry_can_fallback_to_single_source_first(self):
        registry = {
            "default_policy": "single_source_notebook",
            "default_extraction_mode": "single_source_first",
            "topics": [
                {
                    "id": "audit-accounting",
                    "label": "Audit and Accounting",
                    "notebook_id": "nb_audit",
                    "reuse_policy": "topic",
                    "routing_keywords": ["감사"],
                    "sources": [],
                }
            ],
        }

        decision = resolve_notebook(
            registry,
            "1NewAuditPdf",
            title="감사 체크리스트",
        )

        self.assertEqual(decision["extraction_mode"], "single_source_first")
        self.assertEqual(decision["extraction_notebook_action"], "create_single_source_notebook")
        self.assertEqual(decision["topic_notebook_action"], "add_source_after_extraction")

    def test_unknown_topic_falls_back_to_single_source_notebook(self):
        decision = resolve_notebook(
            self.registry,
            "1UnknownPdf",
            title="Unclassified vendor deck",
        )

        self.assertIsNone(decision["topic_id"])
        self.assertEqual(decision["notebook_action"], "create_single_source_notebook")
        self.assertEqual(decision["notebook_title"], "Wiki: Unclassified vendor deck")
        self.assertEqual(decision["source_action"], "add_source")
        self.assertEqual(decision["extraction_mode"], "source_scoped_topic_query")

    def test_invalid_explicit_topic_raises_clear_error(self):
        with self.assertRaisesRegex(RegistryError, "Unknown topic"):
            resolve_notebook(
                self.registry,
                "1UnknownPdf",
                title="Any document",
                explicit_topic="missing-topic",
            )

    def test_decision_is_json_serializable(self):
        decision = resolve_notebook(
            self.registry,
            "1NewStablecoinPdf",
            title="stablecoin settlement report",
        )

        json.dumps(decision, ensure_ascii=False)

    def test_targeted_query_prompt_limits_primary_answer_to_target_pdf(self):
        prompt = build_targeted_query_prompt(
            title="K-IFRS 1109 금융상품",
            drive_file_id="1ExistingAuditPdf",
            source_id="src_existing",
            topic_id="audit-accounting",
        )

        self.assertIn("대상 PDF만", prompt)
        self.assertIn("source_id: src_existing", prompt)
        self.assertIn("drive_file_id: 1ExistingAuditPdf", prompt)
        self.assertIn("topic_notebook_context", prompt)
        self.assertIn("가능하면 NotebookLM query에서 이 source_id만 대상으로 지정해", prompt)
        self.assertIn("비교/연결 섹션", prompt)
        self.assertIn("다른 PDF의 내용을 대상 PDF의 내용처럼 쓰지 마", prompt)


if __name__ == "__main__":
    unittest.main()
