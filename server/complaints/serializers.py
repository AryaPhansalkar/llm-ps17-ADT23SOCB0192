"""Validation of request bodies."""

from django.conf import settings
from rest_framework import serializers


def single_spaced(value: str) -> str:
    """'  Asha   Rao ' -> 'Asha Rao'. Also removes line breaks, which have no place in a name or room."""
    return " ".join(value.split())


class ComplaintSerializer(serializers.Serializer):
    name = serializers.CharField(
        min_length=2,
        max_length=settings.NAME_MAX_CHARS,
        error_messages={
            "blank": "Enter your name.",
            "min_length": "Enter your full name.",
            "max_length": f"Keep the name under {settings.NAME_MAX_CHARS} characters.",
        },
    )
    room = serializers.CharField(
        max_length=settings.ROOM_MAX_CHARS,
        error_messages={
            "blank": "Enter your room number.",
            "max_length": f"Keep the room number under {settings.ROOM_MAX_CHARS} characters.",
        },
    )
    complaint = serializers.CharField(
        min_length=settings.COMPLAINT_MIN_CHARS,
        max_length=settings.COMPLAINT_MAX_CHARS,
        error_messages={
            "blank": "Describe the problem.",
            "min_length": "Describe the problem in a few more words.",
            "max_length": f"Keep the complaint under {settings.COMPLAINT_MAX_CHARS:,} characters.",
        },
    )

    def validate_name(self, value: str) -> str:
        return single_spaced(value)

    def validate_room(self, value: str) -> str:
        return single_spaced(value)
