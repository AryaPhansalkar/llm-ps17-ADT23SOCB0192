"""Tests for the Claude call, with the Anthropic client replaced by a fake."""

from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from complaints import llm

RESULT = llm.Classification(category="water", urgency="medium", summary="Leaking tap in washroom")


def claude_reply(parsed=RESULT, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed)


@override_settings(ANTHROPIC_API_KEY="sk-test", CLAUDE_MODEL="claude-opus-5-5")
class ClassifyTests(SimpleTestCase):
    def setUp(self):
        patcher = mock.patch("complaints.llm._client")
        self.parse = patcher.start().return_value.beta.messages.parse
        self.addCleanup(patcher.stop)
        self.parse.return_value = claude_reply()

    def test_returns_claudes_classification(self):
        self.assertEqual(llm.classify("The tap is leaking."), RESULT)

    def test_sends_the_complaint_and_asks_for_the_classification_shape(self):
        llm.classify("The tap is leaking.")

        request = self.parse.call_args.kwargs
        self.assertEqual(request["model"], "claude-opus-5-5")
        self.assertIs(request["output_format"], llm.Classification)
        self.assertEqual(request["messages"][0]["content"], "<complaint>\nThe tap is leaking.\n</complaint>")

    def test_only_known_categories_and_urgencies_are_accepted(self):
        with self.assertRaises(ValueError):
            llm.Classification(category="plumbing", urgency="medium", summary="x")
        with self.assertRaises(ValueError):
            llm.Classification(category="water", urgency="critical", summary="x")

    @override_settings(CLAUDE_MODEL="claude-haiku-5-5")
    def test_leaves_out_the_fallback_option_for_models_that_do_not_support_it(self):
        llm.classify("The tap is leaking.")

        self.assertNotIn("fallbacks", self.parse.call_args.kwargs)

    def test_a_refusal_is_an_error(self):
        self.parse.return_value = claude_reply(parsed=None, stop_reason="refusal")

        with self.assertRaisesMessage(llm.ClassificationError, "declined"):
            llm.classify("The tap is leaking.")

    def test_an_unreadable_answer_is_an_error(self):
        self.parse.side_effect = ValueError("invalid JSON")

        with self.assertRaisesMessage(llm.ClassificationError, "could not be read"):
            llm.classify("The tap is leaking.")

    @override_settings(ANTHROPIC_API_KEY="")
    def test_a_missing_api_key_is_an_error_and_nothing_is_sent(self):
        with self.assertRaisesMessage(llm.ClassificationError, "ANTHROPIC_API_KEY"):
            llm.classify("The tap is leaking.")

        self.parse.assert_not_called()
