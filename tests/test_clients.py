from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "snippets" / "python"))
sys.path.insert(0, str(ROOT / "soak"))

from ge_streamassist import AssistResult, _iter_json_array  # noqa: E402
from soak.config import Config  # noqa: E402
from soak.http import Api, CallRecord, _excerpt, _safe_error_message  # noqa: E402


class FakeResponse:
    def __init__(self, chunks: list[bytes]):
        self.chunks = chunks

    def iter_content(self, chunk_size=None, decode_unicode=True):
        decoder = None
        if decode_unicode:
            import codecs

            decoder = codecs.getincrementaldecoder("utf-8")()
        for chunk in self.chunks:
            yield decoder.decode(chunk) if decoder else chunk


class StreamParserTests(unittest.TestCase):
    def test_incremental_json_array_handles_boundaries(self):
        raw = json.dumps([{"text": "café"}, {"state": "SUCCEEDED"}], ensure_ascii=False).encode()
        response = FakeResponse([raw[:7], raw[7:14], raw[14:18], raw[18:]])
        self.assertEqual(
            list(_iter_json_array(response)),
            [{"text": "café"}, {"state": "SUCCEEDED"}],
        )

    def test_midstream_error_is_not_silenced(self):
        result = AssistResult()
        with self.assertRaises(RuntimeError):
            result.add_chunk({"error": {"status": "FAILED_PRECONDITION"}})

    def test_truncated_stream_is_rejected(self):
        response = FakeResponse([b'[{"state":"IN_PROGRESS"}'])
        with self.assertRaises(ValueError):
            list(_iter_json_array(response))


class SoakRecordTests(unittest.TestCase):
    def test_payload_excerpt_records_shape_not_content(self):
        excerpt = _excerpt({"query": {"text": "private prompt"}, "token": "secret"})
        rendered = json.dumps(excerpt)
        self.assertNotIn("private prompt", rendered)
        self.assertNotIn("secret", rendered)
        self.assertEqual(excerpt["query"]["text"]["chars"], 14)

    def test_error_scrubber_removes_urls_and_bearer_tokens(self):
        value = _safe_error_message("open https://example.test/?state=abc with Bearer token.value")
        self.assertNotIn("state=abc", value)
        self.assertNotIn("token.value", value)

    def test_serialized_call_omits_answer_text(self):
        record = CallRecord("probe", "streamAssist", "POST", "path", "v1", text="private answer")
        payload = record.to_dict()
        self.assertEqual(payload["text_chars"], 14)
        self.assertNotIn("text_head", payload)
        self.assertNotIn("private answer", json.dumps(payload))
        self.assertIn("request_shape", payload)
        self.assertNotIn("request_excerpt", payload)

    def test_stream_version_uses_alpha_only_when_needed(self):
        cfg = Config(
            project_id="p", project_number="123", location="global", app_id="a",
            assistant_id="default_assistant", api_version="v1", bucket=None,
            a2a_agent_id="a2a", data_store_id="ds",
            model_id="model", license_limit=0, license_count=0,
            license_edition="unconfigured", git_sha="test", region="us-central1",
        )
        api = object.__new__(Api)
        api.cfg = cfg
        api.request = Mock(return_value=CallRecord("x", "streamAssist", "POST", "p", "v1"))
        api.stream_assist("stable", {"query": {"text": "hi"}})
        self.assertIsNone(api.request.call_args.kwargs["version"])
        api.stream_assist("alpha", {"query": {"text": "hi"}, "isSessionLess": True})
        self.assertEqual(api.request.call_args.kwargs["version"], "v1alpha")

    def test_a2a_authorization_handoff_is_detected_without_storing_url(self):
        api = object.__new__(Api)
        record = CallRecord("a2a", "a2a.message:stream", "POST", "path", "v1")
        api._absorb_a2a_item(record, {
            "message": {
                "role": "ROLE_AGENT",
                "metadata": {
                    "requiredAuthorizations": [{"authorizationUri": "https://secret.test/?state=abc"}]
                },
            }
        })
        self.assertTrue(record.handoff_required)
        self.assertEqual(record.required_authorizations, 1)
        self.assertNotIn("secret.test", json.dumps(record.to_dict()))


if __name__ == "__main__":
    unittest.main()
