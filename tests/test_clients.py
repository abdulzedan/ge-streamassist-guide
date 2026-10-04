from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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

    def test_result_collects_current_response_metadata(self):
        result = AssistResult()
        result.add_chunk({
            "invocationTools": ["web_grounding"],
            "invokedSkills": [{"name": "skills/one", "displayName": "One"}],
            "connectorAuthErrors": [{"dataConnector": "connectors/one"}],
            "statusUpdates": [{"status": "WORKING"}],
            "finalResultToolInvocationId": "tool-7",
            "answer": {"state": "SUCCEEDED"},
        })
        self.assertEqual(result.invocation_tools, ["web_grounding"])
        self.assertEqual(result.invoked_skills[0]["displayName"], "One")
        self.assertEqual(len(result.connector_auth_errors), 1)
        self.assertEqual(len(result.status_updates), 1)
        self.assertEqual(result.final_result_tool_invocation_id, "tool-7")

    def test_sessionless_final_chunk_clears_synthetic_session(self):
        result = AssistResult()
        result.add_chunk({
            "answer": {"state": "IN_PROGRESS"},
            "sessionInfo": {"session": "projects/p/sessions/session-less-123"},
        })
        result.add_chunk({
            "answer": {"state": "SUCCEEDED"},
            "sessionInfo": {"queryId": "query-1"},
        })
        self.assertIsNone(result.session)

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
            license_edition="unconfigured", billing_model="unknown",
            git_sha="test", region="us-central1",
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

    def test_a2a_send_response_is_absorbed(self):
        api = object.__new__(Api)
        record = CallRecord("a2a", "a2a.message:send", "POST", "path", "v1")
        api._absorb_a2a_item(record, {
            "message": {
                "role": "ROLE_AGENT",
                "contextId": "projects/123/locations/global/sessions/7",
                "content": [{"text": "done"}],
            }
        })
        self.assertEqual(record.text, "done")
        self.assertEqual(record.session_id, "7")
        self.assertIn("ROLE_AGENT", record.a2a_roles)

    def test_current_response_metadata_is_recorded_without_connector_error_text(self):
        api = object.__new__(Api)
        record = CallRecord("probe", "streamAssist", "POST", "path", "v1")
        api._absorb_answer_chunk(record, {
            "invocationTools": ["web_grounding"],
            "invokedSkills": [{"name": "skills/one"}],
            "connectorAuthErrors": [{
                "dataConnector": "connectors/private",
                "errorMessage": "secret auth detail",
            }],
            "statusUpdates": [{"status": "WORKING"}],
            "finalResultToolInvocationId": "tool-7",
        })
        payload = record.to_dict()
        self.assertEqual(payload["invocation_tools"], ["web_grounding"])
        self.assertEqual(payload["invoked_skills"], ["skills/one"])
        self.assertEqual(payload["connector_auth_errors"], 1)
        self.assertEqual(payload["status_updates"], 1)
        self.assertTrue(payload["final_result_from_tool"])
        self.assertNotIn("secret auth detail", json.dumps(payload))

    def test_soak_record_clears_sessionless_synthetic_session(self):
        api = object.__new__(Api)
        record = CallRecord("probe", "streamAssist", "POST", "path", "v1alpha")
        api._absorb_answer_chunk(record, {
            "answer": {"state": "IN_PROGRESS"},
            "sessionInfo": {"session": "projects/p/sessions/session-less-123"},
        })
        api._absorb_answer_chunk(record, {
            "answer": {"state": "SUCCEEDED"},
            "sessionInfo": {"queryId": "query-1"},
        })
        self.assertIsNone(record.session)


class ClientRequestTests(unittest.TestCase):
    def client(self):
        from ge_streamassist import GEClient

        ge = GEClient(project_id="project", app_id="app", project_number="123")
        ge._headers = Mock(return_value={})
        return ge

    def test_streamassist_rejects_non_numeric_registered_agent_id(self):
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            list(self.client().stream_assist(query="hello", agent_id="named-agent"))

    @patch("ge_streamassist.requests.post")
    def test_a2a_generates_a_unique_message_id(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"message": {}}
        ge = self.client()
        ge.a2a_message_send("42", "first")
        ge.a2a_message_send("42", "second")
        first = post.call_args_list[0].kwargs["json"]["message"]["messageId"]
        second = post.call_args_list[1].kwargs["json"]["message"]["messageId"]
        self.assertNotEqual(first, second)

    @patch("ge_streamassist.requests.post")
    def test_a2a_uses_registry_endpoint_verbatim(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"message": {}}
        self.client().a2a_message_send(
            "42", "hello", endpoint_url="https://example.test/registered/a2a"
        )
        self.assertEqual(
            post.call_args.args[0],
            "https://example.test/registered/a2a/v1/message:send",
        )

    @patch("ge_streamassist.requests.post")
    def test_assist_supports_current_stable_request_fields(self, post):
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"answer": {"state": "SUCCEEDED"}}
        self.client().assist(
            file_ids=["file-1"],
            force_assist=True,
            user_metadata={"preferredLanguageCode": "fr-CA"},
        )
        self.assertEqual(post.call_args.kwargs["json"], {
            "fileIds": ["file-1"],
            "assistSkippingMode": "REQUEST_ASSIST",
            "userMetadata": {"preferredLanguageCode": "fr-CA"},
        })

    def test_assist_requires_query_or_files(self):
        with self.assertRaisesRegex(ValueError, "query or file_ids"):
            self.client().assist()


if __name__ == "__main__":
    unittest.main()
