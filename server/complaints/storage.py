"""Saves complaints by appending them to a CSV file.

The file is the hostel office's record, so it is written to be opened directly
in Excel or Google Sheets: one row per complaint, a header row, local times.
"""

import csv
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from filelock import FileLock, Timeout

FIELDS = ["complaint_id", "submitted_at", "name", "room", "category", "urgency", "summary", "complaint"]

ID_PATTERN = re.compile(r"^CMP-(\d+)$")

# A spreadsheet treats a cell that starts with one of these as a formula. The
# file holds text typed by anyone and is opened by staff, so such cells are
# written as plain text (OWASP's "CSV injection" guidance).
FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


class StorageError(Exception):
    """The complaint could not be written to the file."""


@dataclass(frozen=True)
class Complaint:
    complaint_id: str
    submitted_at: datetime
    name: str
    room: str
    category: str
    urgency: str
    summary: str
    complaint: str


def save(*, name: str, room: str, complaint: str, category: str, urgency: str, summary: str) -> Complaint:
    """Append a complaint to the file and return it with its new ID.

    Two complaints arriving at the same moment are written one after the other:
    the lock makes "read the last ID, write the next row" a single step, even
    across several server processes.
    """
    path = Path(settings.COMPLAINTS_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(f"{path}.lock", timeout=10):
            record = Complaint(
                complaint_id=f"CMP-{_last_number(path) + 1:04d}",
                submitted_at=timezone.localtime(),
                name=name,
                room=room,
                category=category,
                urgency=urgency,
                summary=summary,
                complaint=complaint,
            )
            _append(path, record)
    except Timeout as error:
        raise StorageError("The complaints file is busy.") from error
    except OSError as error:
        # On Windows this happens when the file is open in Excel.
        raise StorageError(f"The complaints file could not be written: {error}") from error
    return record


def _last_number(path: Path) -> int:
    """The highest complaint number in the file, or 0 if there are none yet."""
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8-sig") as file:
        numbers = [
            int(match.group(1))
            for row in csv.DictReader(file)
            if (match := ID_PATTERN.match(row.get("complaint_id") or ""))
        ]
    return max(numbers, default=0)


def _append(path: Path, record: Complaint) -> None:
    is_new = not path.exists() or path.stat().st_size == 0
    row = asdict(record) | {"submitted_at": record.submitted_at.strftime("%Y-%m-%d %H:%M:%S")}

    # A new file starts with a UTF-8 byte-order mark ("utf-8-sig"); without it
    # Excel misreads names and complaints written in non-Latin scripts.
    with path.open("a", newline="", encoding="utf-8-sig" if is_new else "utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({field: _as_plain_text(str(row[field])) for field in FIELDS})


def _as_plain_text(cell: str) -> str:
    return f"'{cell}" if cell.startswith(FORMULA_TRIGGERS) else cell
