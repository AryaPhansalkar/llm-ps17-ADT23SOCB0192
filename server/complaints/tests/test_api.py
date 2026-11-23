"""Tests for the HTTP API. Claude is never called: the classifier is replaced."""

import csv
import tempfile
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.throttling import ScopedRateThrottle

from complaints import llm, storage

URL = "/api/v1/complaints/"
BODY = {"name": "Asha Rao", "room": "B-204", "complaint": "Sparks are coming from the switchboard."}
CLASSIFICATION = llm.Classification(
    category="electrical", urgency="high", summary="Sparks from switchboard in B-204"
)


class ApiTestCase(SimpleTestCase):
    def setUp(self):
        cache.clear()  # reset the rate-limit counters between tests

        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "complaints.csv"
        settings = override_settings(COMPLAINTS_FILE=self.path)
        settings.enable()
        self.addCleanup(settings.disable)

        patcher = mock.patch("complaints.views.llm.classify", return_value=CLASSIFICATION)
        self.classify = patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, body):
        return self.client.post(URL, body, content_type="application/json")

    def saved_rows(self):
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))


class SubmitComplaintTests(ApiTestCase):
    def test_returns_the_id_category_and_urgency(self):
        response = self.post(BODY)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["id"], "CMP-0001")
        self.assertEqual(
            {key: body[key] for key in ("category", "urgency", "summary", "classified")},
            {
                "category": "electrical",
                "urgency": "high",
                "summary": "Sparks from switchboard in B-204",
                "classified": True,
            },
        )

    def test_saves_the_complaint_to_the_file(self):
        self.post(BODY)

        (row,) = self.saved_rows()
        self.assertEqual(row["complaint_id"], "CMP-0001")
        self.assertEqual((row["name"], row["room"], row["complaint"]), tuple(BODY.values()))
        self.assertEqual((row["category"], row["urgency"]), ("electrical", "high"))

    def test_sends_only_the_complaint_text_to_the_classifier(self):
        self.post(BODY)

        self.classify.assert_called_once_with(BODY["complaint"])

    def test_tidies_spacing_in_the_name_and_room(self):
        self.post(BODY | {"name": "  Asha   Rao ", "room": " B-204\n"})

        (row,) = self.saved_rows()
        self.assertEqual((row["name"], row["room"]), ("Asha Rao", "B-204"))

    def test_rejects_missing_or_empty_fields_and_saves_nothing(self):
        for field in BODY:
            for bad_body in ({**BODY, field: "   "}, {k: v for k, v in BODY.items() if k != field}):
                with self.subTest(field=field, body=bad_body):
                    response = self.post(bad_body)

                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.json())
        self.assertEqual(self.saved_rows(), [])
        self.classify.assert_not_called()

    def test_rejects_text_over_the_length_limits(self):
        for field, length in (("name", 81), ("room", 21), ("complaint", 1001)):
            with self.subTest(field=field):
                response = self.post(BODY | {field: "x" * length})

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())

    def test_limits_how_fast_one_client_can_submit(self):
        with mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"complaints": "2/min"}):
            statuses = [self.post(BODY).status_code for _ in range(3)]

        self.assertEqual(statuses, [201, 201, 429])
        self.assertEqual(len(self.saved_rows()), 2)


class WhenClassificationFailsTests(ApiTestCase):
    def test_the_complaint_is_still_saved_and_marked_unclassified(self):
        self.classify.side_effect = llm.ClassificationError("The Claude API rate limit was reached.")

        response = self.post(BODY)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual((body["id"], body["classified"]), ("CMP-0001", False))
        self.assertEqual((body["category"], body["urgency"]), ("unclassified", "unclassified"))
        (row,) = self.saved_rows()
        self.assertEqual((row["complaint"], row["category"]), (BODY["complaint"], "unclassified"))

    def test_an_unexpected_classifier_error_does_not_lose_the_complaint(self):
        self.classify.side_effect = RuntimeError("bug")

        with self.assertLogs("complaints.views", level="ERROR"):
            response = self.post(BODY)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.saved_rows()), 1)

    @override_settings(DEBUG=True)
    def test_the_reason_is_included_in_debug_mode(self):
        self.classify.side_effect = llm.ClassificationError("The server has no Claude API key.")

        self.assertEqual(
            self.post(BODY).json()["classification_problem"], "The server has no Claude API key."
        )

    @override_settings(DEBUG=False)
    def test_the_reason_is_hidden_outside_debug_mode(self):
        self.classify.side_effect = llm.ClassificationError("The server has no Claude API key.")

        self.assertNotIn("classification_problem", self.post(BODY).json())


class WhenSavingFailsTests(ApiTestCase):
    def test_says_the_complaint_was_not_saved(self):
        with mock.patch("complaints.views.storage.save", side_effect=storage.StorageError("disk full")):
            with self.assertLogs("complaints.views", level="ERROR"):
                response = self.post(BODY)

        self.assertEqual(response.status_code, 503)
        self.assertIn("could not be saved", response.json()["detail"])


class HealthTests(ApiTestCase):
    @override_settings(ANTHROPIC_API_KEY="sk-test", CLAUDE_MODEL="claude-opus-5-5")
    def test_reports_status_without_revealing_the_key(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(
            response.json(), {"status": "ok", "model": "claude-opus-5-5", "api_key_configured": True}
        )
