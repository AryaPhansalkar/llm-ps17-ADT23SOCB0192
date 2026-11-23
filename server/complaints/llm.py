"""Calls Claude to classify a complaint.

Only the complaint text is sent. The student's name and room are not needed to
classify it, so they never leave the server.
"""

import logging
from functools import lru_cache
from typing import Literal

import anthropic
from django.conf import settings
from pydantic import BaseModel

from . import prompts

logger = logging.getLogger(__name__)

# If Claude's safety filters decline a request (a complaint about violence or
# harassment could trigger this), the API re-runs it on a fallback model
# instead of failing. Only these models accept that option.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MODELS_WITH_FALLBACK = {
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
    "claude-fable-5-2",
    "claude-fable-5-1",
}

Category = Literal[
    "electrical", "water", "mess", "internet", "cleanliness", "maintenance", "security", "other"
]
Urgency = Literal["low", "medium", "high"]


class Classification(BaseModel):
    """The shape of Claude's answer. The API guarantees the reply is JSON matching it."""

    category: Category
    urgency: Urgency
    summary: str


class ClassificationError(Exception):
    """Claude could not classify the complaint. The message says why, in plain words."""


@lru_cache(maxsize=1)
def _client() -> anthropic.Anthropic:
    # One shared client reuses its HTTP connections across requests. The timeout is
    # short because a student is waiting, and an unclassified complaint is still saved.
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=2, timeout=30.0)


def classify(complaint: str) -> Classification:
    """Return the category, urgency and one-line summary for a complaint.

    Raises ClassificationError if Claude cannot be reached or gives no usable answer.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise ClassificationError("The server has no Claude API key. Add ANTHROPIC_API_KEY to server/.env.")

    model = settings.CLAUDE_MODEL
    fallback = {"betas": [FALLBACK_BETA], "fallbacks": "default"} if model in MODELS_WITH_FALLBACK else {}

    try:
        response = _client().beta.messages.parse(
            model=model,
            max_tokens=16000,
            system=prompts.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompts.user_message(complaint)}],
            output_format=Classification,
            output_config={"effort": "low"},
            **fallback,
        )
    except anthropic.AuthenticationError as error:
        raise ClassificationError(
            "The Claude API key was rejected. Check ANTHROPIC_API_KEY in server/.env."
        ) from error
    except anthropic.PermissionDeniedError as error:
        raise ClassificationError(f"This API key is not allowed to use the model {model}.") from error
    except anthropic.NotFoundError as error:
        raise ClassificationError(f"Claude model '{model}' was not found. Check CLAUDE_MODEL.") from error
    except anthropic.RateLimitError as error:
        raise ClassificationError("The Claude API rate limit was reached.") from error
    except anthropic.APIConnectionError as error:
        raise ClassificationError("The server couldn't reach the Claude API.") from error
    except anthropic.APIStatusError as error:
        raise ClassificationError(f"The Claude API returned an error ({error.status_code}).") from error
    except ValueError as error:
        # The reply was not valid JSON for the Classification shape (for example, it was cut off).
        raise ClassificationError("Claude's answer could not be read.") from error

    if response.stop_reason == "refusal":
        raise ClassificationError("Claude declined to classify this complaint.")
    if response.parsed_output is None:
        raise ClassificationError("Claude's answer was incomplete.")

    return response.parsed_output
