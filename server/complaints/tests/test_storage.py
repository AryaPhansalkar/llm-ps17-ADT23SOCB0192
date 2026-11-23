import csv
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, override_settings

from complaints import storage

COMPLAINT = {
    "name": "Asha Rao",
    "room": "B-204",
    "complaint": "The fan in my room is not working.",
    "category": "electrical",
    "urgency": "medium",
    "summary": "Fan not working in B-204",
}


class StorageTestCase(SimpleTestCase):
    """Each test writes to its own temporary complaints file."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "data" / "complaints.csv"
        settings = override_settings(COMPLAINTS_FILE=self.path, TIME_ZONE="Asia/Kolkata")
        settings.enable()
        self.addCleanup(settings.disable)

    def rows(self):
        with self.path.open(newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))


class SaveTests(StorageTestCase):
    def test_creates_the_folder_and_file_with_a_header_row(self):
        storage.save(**COMPLAINT)

        header = self.path.read_text(encoding="utf-8-sig").splitlines()[0]
        self.assertEqual(header, "complaint_id,submitted_at,name,room,category,urgency,summary,complaint")

    def test_writes_every_field_of_the_complaint(self):
        record = storage.save(**COMPLAINT)

        row = self.rows()[0]
        self.assertEqual(row["complaint_id"], "CMP-0001")
        self.assertEqual(row["submitted_at"], record.submitted_at.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual({field: row[field] for field in COMPLAINT}, COMPLAINT)

    def test_ids_count_up_and_the_header_is_written_once(self):
        ids = [storage.save(**COMPLAINT).complaint_id for _ in range(3)]

        self.assertEqual(ids, ["CMP-0001", "CMP-0002", "CMP-0003"])
        self.assertEqual(self.path.read_text(encoding="utf-8-sig").count("complaint_id"), 1)

    def test_an_id_is_not_reused_after_staff_delete_earlier_rows(self):
        for _ in range(3):
            storage.save(**COMPLAINT)
        lines = self.path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
        self.path.write_text(lines[0] + lines[3], encoding="utf-8-sig")  # keep only CMP-0003

        self.assertEqual(storage.save(**COMPLAINT).complaint_id, "CMP-0004")

    def test_time_is_recorded_in_the_configured_time_zone(self):
        record = storage.save(**COMPLAINT)

        self.assertEqual(record.submitted_at.utcoffset().total_seconds(), 5.5 * 3600)

    def test_keeps_commas_quotes_line_breaks_and_other_scripts_intact(self):
        text = 'Tap leaks, badly.\nWarden said "wait".'
        storage.save(**COMPLAINT | {"name": "आशा राव", "complaint": text})

        row = self.rows()[0]
        self.assertEqual(row["name"], "आशा राव")
        self.assertEqual(row["complaint"], text)

    def test_file_starts_with_a_byte_order_mark_so_excel_reads_utf8(self):
        storage.save(**COMPLAINT)
        storage.save(**COMPLAINT)

        data = self.path.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(data.count(b"\xef\xbb\xbf"), 1)

    def test_text_that_looks_like_a_formula_is_written_as_plain_text(self):
        storage.save(**COMPLAINT | {"name": "=HYPERLINK(1)", "room": "+12", "complaint": "@SUM(A1) -1"})

        row = self.rows()[0]
        self.assertEqual(
            (row["name"], row["room"], row["complaint"]), ("'=HYPERLINK(1)", "'+12", "'@SUM(A1) -1")
        )

    def test_complaints_saved_at_the_same_moment_get_different_ids(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(lambda _: storage.save(**COMPLAINT).complaint_id, range(24)))

        self.assertEqual(sorted(ids), [f"CMP-{number:04d}" for number in range(1, 25)])
        self.assertEqual(len(self.rows()), 24)

    def test_a_file_that_cannot_be_written_raises_storage_error(self):
        with mock.patch.object(Path, "open", side_effect=PermissionError("file is open in Excel")):
            with self.assertRaises(storage.StorageError):
                storage.save(**COMPLAINT)
