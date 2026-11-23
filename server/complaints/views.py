import logging

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import llm, storage
from .serializers import ComplaintSerializer

logger = logging.getLogger(__name__)

# Written to the file when Claude could not classify a complaint, so staff can
# find these rows and sort them by hand.
UNCLASSIFIED = "unclassified"


class ComplaintNotSaved(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "complaint_not_saved"
    default_detail = "Your complaint could not be saved. Please try again in a moment."


class HealthView(APIView):
    """GET: is the server up, and does it have what it needs to classify complaints?"""

    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "model": settings.CLAUDE_MODEL,
                "api_key_configured": bool(settings.ANTHROPIC_API_KEY),
            }
        )


class ComplaintView(APIView):
    """POST {"name", "room", "complaint"} -> 201 with the complaint ID, category and urgency.

    A complaint is always saved, even when it cannot be classified: losing it
    would be worse than filing it unsorted.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "complaints"

    def post(self, request: Request) -> Response:
        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data

        problem = None
        try:
            result = llm.classify(fields["complaint"])
            labels = {
                "category": result.category,
                "urgency": result.urgency,
                "summary": result.summary.strip(),
            }
        except llm.ClassificationError as error:
            problem = str(error)
        except Exception:
            # Whatever goes wrong while classifying, the complaint must still be saved.
            logger.exception("Unexpected error while classifying a complaint")
            problem = "Unexpected error while classifying; see the server log."
        if problem:
            labels = {"category": UNCLASSIFIED, "urgency": UNCLASSIFIED, "summary": ""}

        try:
            record = storage.save(**fields, **labels)
        except storage.StorageError as error:
            logger.error("Complaint not saved: %s", error)
            raise ComplaintNotSaved() from error

        # The log records what happened without the student's name or words.
        if problem:
            logger.warning("Saved %s unclassified: %s", record.complaint_id, problem)
        else:
            logger.info("Saved %s (%s, %s urgency)", record.complaint_id, record.category, record.urgency)

        body = {
            "id": record.complaint_id,
            "submitted_at": record.submitted_at.isoformat(timespec="seconds"),
            "category": record.category,
            "urgency": record.urgency,
            "summary": record.summary,
            "classified": problem is None,
        }
        if problem and settings.DEBUG:
            body["classification_problem"] = problem  # helps while developing; hidden in production
        return Response(body, status=status.HTTP_201_CREATED)
