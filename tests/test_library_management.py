import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from library_management.database import LibraryDatabase


class LibraryManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = ROOT / ".tmp-tests"
        self.temp_root.mkdir(exist_ok=True)
        self.db_path = self.temp_root / "test_library_management.db"
        self.db_path.unlink(missing_ok=True)
        self.db = LibraryDatabase(self.db_path, seed=False)
        self.member = self.db.create_member(
            {"name": "Anaya Rao", "address": "14 North Street", "phone": "9000000001"}
        )
        self.book = self.db.create_book(
            {
                "title": "Data Modeling",
                "author": "Chen",
                "publisher": "Library Press",
                "year": 2024,
                "available_copies": 1,
            }
        )
        self.librarian = self.db.create_librarian({"name": "Kiran Shah"})

    def tearDown(self) -> None:
        self.db_path.unlink(missing_ok=True)

    def test_issue_book_decrements_available_copies(self) -> None:
        issue = self.db.issue_book(
            {
                "member_id": self.member["member_id"],
                "book_id": self.book["book_id"],
                "librarian_id": self.librarian["librarian_id"],
                "issue_date": "2026-06-02",
            }
        )

        books = self.db.list_books()
        self.assertEqual(issue["status"], "Issued")
        self.assertEqual(books[0]["available_copies"], 0)

    def test_return_book_sets_return_date_and_restores_copy(self) -> None:
        issue = self.db.issue_book(
            {
                "member_id": self.member["member_id"],
                "book_id": self.book["book_id"],
                "librarian_id": self.librarian["librarian_id"],
                "issue_date": "2026-06-02",
            }
        )

        returned = self.db.return_book(issue["issue_id"], {"return_date": "2026-06-05"})

        self.assertEqual(returned["status"], "Returned")
        self.assertEqual(returned["return_date"], "2026-06-05")
        self.assertEqual(self.db.list_books()[0]["available_copies"], 1)

    def test_unavailable_book_cannot_be_issued(self) -> None:
        payload = {
            "member_id": self.member["member_id"],
            "book_id": self.book["book_id"],
            "librarian_id": self.librarian["librarian_id"],
            "issue_date": "2026-06-02",
        }
        self.db.issue_book(payload)

        with self.assertRaises(ValueError):
            self.db.issue_book(payload)

    def test_issue_history_prevents_deleting_linked_book(self) -> None:
        self.db.issue_book(
            {
                "member_id": self.member["member_id"],
                "book_id": self.book["book_id"],
                "librarian_id": self.librarian["librarian_id"],
                "issue_date": "2026-06-02",
            }
        )

        with self.assertRaises(ValueError):
            self.db.delete_book(self.book["book_id"])


if __name__ == "__main__":
    unittest.main()

