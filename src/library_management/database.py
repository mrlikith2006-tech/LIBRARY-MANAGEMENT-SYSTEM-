from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DATE_FORMAT = "%Y-%m-%d"
LOAN_DAYS = 14


class LibraryDatabase:
    """SQLite data layer for the library management schema."""

    def __init__(self, path: Path | str, seed: bool = True) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()
        if seed:
            self.seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS "Member" (
                    MemberID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL CHECK(length(Name) BETWEEN 1 AND 50),
                    Address TEXT NOT NULL CHECK(length(Address) BETWEEN 1 AND 100),
                    Phone TEXT NOT NULL CHECK(length(Phone) BETWEEN 1 AND 15)
                );

                CREATE TABLE IF NOT EXISTS "Book" (
                    BookID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Title TEXT NOT NULL CHECK(length(Title) BETWEEN 1 AND 50),
                    Author TEXT NOT NULL CHECK(length(Author) BETWEEN 1 AND 50),
                    Publisher TEXT NOT NULL CHECK(length(Publisher) BETWEEN 1 AND 50),
                    Year INTEGER NOT NULL CHECK(Year BETWEEN 1400 AND 2200),
                    Available_Copies INTEGER NOT NULL DEFAULT 0 CHECK(Available_Copies >= 0)
                );

                CREATE TABLE IF NOT EXISTS "Librarian" (
                    LibrarianID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL CHECK(length(Name) BETWEEN 1 AND 50)
                );

                CREATE TABLE IF NOT EXISTS "Issue" (
                    IssueID INTEGER PRIMARY KEY AUTOINCREMENT,
                    MemberID INTEGER NOT NULL,
                    BookID INTEGER NOT NULL,
                    LibrarianID INTEGER NOT NULL,
                    IssueDate TEXT NOT NULL,
                    ReturnDate TEXT,
                    FOREIGN KEY(MemberID) REFERENCES "Member"(MemberID) ON DELETE RESTRICT,
                    FOREIGN KEY(BookID) REFERENCES "Book"(BookID) ON DELETE RESTRICT,
                    FOREIGN KEY(LibrarianID) REFERENCES "Librarian"(LibrarianID) ON DELETE RESTRICT,
                    CHECK(ReturnDate IS NULL OR ReturnDate >= IssueDate)
                );

                CREATE INDEX IF NOT EXISTS idx_issue_member ON "Issue"(MemberID);
                CREATE INDEX IF NOT EXISTS idx_issue_book ON "Issue"(BookID);
                CREATE INDEX IF NOT EXISTS idx_issue_librarian ON "Issue"(LibrarianID);
                CREATE INDEX IF NOT EXISTS idx_issue_active ON "Issue"(ReturnDate);
                """
            )

    def seed_defaults(self) -> None:
        with self._lock, self._connection() as conn:
            count = conn.execute('SELECT COUNT(*) FROM "Member"').fetchone()[0]
            if count:
                return
            conn.executemany(
                'INSERT INTO "Member" (Name, Address, Phone) VALUES (?, ?, ?)',
                [
                    ("Aarav Sharma", "42 Knowledge Park, Bengaluru", "9876543210"),
                    ("Maya Iyer", "18 Central Avenue, Chennai", "9123456780"),
                    ("Rohan Mehta", "7 Green Street, Pune", "9988776655"),
                ],
            )
            conn.executemany(
                """
                INSERT INTO "Book" (Title, Author, Publisher, Year, Available_Copies)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    ("Database System Concepts", "Silberschatz", "McGraw Hill", 2019, 4),
                    ("Clean Code", "Robert Martin", "Prentice Hall", 2008, 2),
                    ("The Pragmatic Programmer", "Hunt Thomas", "Addison Wesley", 2019, 3),
                    ("Python Crash Course", "Eric Matthes", "No Starch", 2023, 5),
                ],
            )
            conn.executemany(
                'INSERT INTO "Librarian" (Name) VALUES (?)',
                [("Priya Nair",), ("Vikram Rao",)],
            )
            conn.execute(
                """
                INSERT INTO "Issue" (MemberID, BookID, LibrarianID, IssueDate, ReturnDate)
                VALUES (1, 2, 1, ?, NULL)
                """,
                ((date.today() - timedelta(days=3)).isoformat(),),
            )
            conn.execute(
                'UPDATE "Book" SET Available_Copies = Available_Copies - 1 WHERE BookID = 2'
            )

    def get_summary(self) -> dict[str, Any]:
        today = date.today()
        overdue_before = (today - timedelta(days=LOAN_DAYS)).isoformat()
        with self._lock, self._connection() as conn:
            member_count = scalar(conn, 'SELECT COUNT(*) FROM "Member"')
            book_count = scalar(conn, 'SELECT COUNT(*) FROM "Book"')
            librarian_count = scalar(conn, 'SELECT COUNT(*) FROM "Librarian"')
            active_issues = scalar(conn, 'SELECT COUNT(*) FROM "Issue" WHERE ReturnDate IS NULL')
            overdue_count = scalar(
                conn,
                'SELECT COUNT(*) FROM "Issue" WHERE ReturnDate IS NULL AND IssueDate < ?',
                (overdue_before,),
            )
            total_available = scalar(conn, 'SELECT COALESCE(SUM(Available_Copies), 0) FROM "Book"')
            low_stock_books = [
                book_from_row(row)
                for row in conn.execute(
                    """
                    SELECT * FROM "Book"
                    WHERE Available_Copies <= 1
                    ORDER BY Available_Copies ASC, Title ASC
                    LIMIT 5
                    """
                )
            ]
        return {
            "member_count": member_count,
            "book_count": book_count,
            "librarian_count": librarian_count,
            "active_issues": active_issues,
            "overdue_count": overdue_count,
            "available_copies": total_available,
            "low_stock_books": low_stock_books,
        }

    def list_members(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute('SELECT * FROM "Member" ORDER BY Name ASC').fetchall()
            return [member_from_row(row) for row in rows]

    def create_member(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload.get("name"), "Name", 50)
        address = clean_text(payload.get("address"), "Address", 100)
        phone = clean_text(payload.get("phone"), "Phone", 15)
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                'INSERT INTO "Member" (Name, Address, Phone) VALUES (?, ?, ?)',
                (name, address, phone),
            )
            row = conn.execute('SELECT * FROM "Member" WHERE MemberID = ?', (cursor.lastrowid,)).fetchone()
            return member_from_row(row)

    def update_member(self, member_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            current = conn.execute('SELECT * FROM "Member" WHERE MemberID = ?', (member_id,)).fetchone()
            if not current:
                raise ValueError("Member not found.")
            name = clean_text(payload.get("name", current["Name"]), "Name", 50)
            address = clean_text(payload.get("address", current["Address"]), "Address", 100)
            phone = clean_text(payload.get("phone", current["Phone"]), "Phone", 15)
            conn.execute(
                'UPDATE "Member" SET Name = ?, Address = ?, Phone = ? WHERE MemberID = ?',
                (name, address, phone, member_id),
            )
            row = conn.execute('SELECT * FROM "Member" WHERE MemberID = ?', (member_id,)).fetchone()
            return member_from_row(row)

    def delete_member(self, member_id: int) -> None:
        self._delete_row("Member", "MemberID", member_id, "member")

    def list_books(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute('SELECT * FROM "Book" ORDER BY Title ASC').fetchall()
            return [book_from_row(row) for row in rows]

    def create_book(self, payload: dict[str, Any]) -> dict[str, Any]:
        title, author, publisher, year, available_copies = clean_book_payload(payload)
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO "Book" (Title, Author, Publisher, Year, Available_Copies)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, author, publisher, year, available_copies),
            )
            row = conn.execute('SELECT * FROM "Book" WHERE BookID = ?', (cursor.lastrowid,)).fetchone()
            return book_from_row(row)

    def update_book(self, book_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            current = conn.execute('SELECT * FROM "Book" WHERE BookID = ?', (book_id,)).fetchone()
            if not current:
                raise ValueError("Book not found.")
            merged = {
                "title": payload.get("title", current["Title"]),
                "author": payload.get("author", current["Author"]),
                "publisher": payload.get("publisher", current["Publisher"]),
                "year": payload.get("year", current["Year"]),
                "available_copies": payload.get("available_copies", current["Available_Copies"]),
            }
            title, author, publisher, year, available_copies = clean_book_payload(merged)
            conn.execute(
                """
                UPDATE "Book"
                SET Title = ?, Author = ?, Publisher = ?, Year = ?, Available_Copies = ?
                WHERE BookID = ?
                """,
                (title, author, publisher, year, available_copies, book_id),
            )
            row = conn.execute('SELECT * FROM "Book" WHERE BookID = ?', (book_id,)).fetchone()
            return book_from_row(row)

    def delete_book(self, book_id: int) -> None:
        self._delete_row("Book", "BookID", book_id, "book")

    def list_librarians(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute('SELECT * FROM "Librarian" ORDER BY Name ASC').fetchall()
            return [librarian_from_row(row) for row in rows]

    def create_librarian(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = clean_text(payload.get("name"), "Name", 50)
        with self._lock, self._connection() as conn:
            cursor = conn.execute('INSERT INTO "Librarian" (Name) VALUES (?)', (name,))
            row = conn.execute(
                'SELECT * FROM "Librarian" WHERE LibrarianID = ?', (cursor.lastrowid,)
            ).fetchone()
            return librarian_from_row(row)

    def update_librarian(self, librarian_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as conn:
            current = conn.execute(
                'SELECT * FROM "Librarian" WHERE LibrarianID = ?', (librarian_id,)
            ).fetchone()
            if not current:
                raise ValueError("Librarian not found.")
            name = clean_text(payload.get("name", current["Name"]), "Name", 50)
            conn.execute('UPDATE "Librarian" SET Name = ? WHERE LibrarianID = ?', (name, librarian_id))
            row = conn.execute('SELECT * FROM "Librarian" WHERE LibrarianID = ?', (librarian_id,)).fetchone()
            return librarian_from_row(row)

    def delete_librarian(self, librarian_id: int) -> None:
        self._delete_row("Librarian", "LibrarianID", librarian_id, "librarian")

    def list_issues(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as conn:
            rows = conn.execute(issue_select_sql() + " ORDER BY i.IssueDate DESC, i.IssueID DESC").fetchall()
            return [issue_from_row(row) for row in rows]

    def issue_book(self, payload: dict[str, Any]) -> dict[str, Any]:
        member_id = clean_positive_int(payload.get("member_id"), "Member")
        book_id = clean_positive_int(payload.get("book_id"), "Book")
        librarian_id = clean_positive_int(payload.get("librarian_id"), "Librarian")
        issue_date = clean_date(payload.get("issue_date") or date.today().isoformat(), "Issue date")
        with self._lock, self._connection() as conn:
            ensure_exists(conn, "Member", "MemberID", member_id, "Member")
            book = ensure_exists(conn, "Book", "BookID", book_id, "Book")
            ensure_exists(conn, "Librarian", "LibrarianID", librarian_id, "Librarian")
            if int(book["Available_Copies"]) <= 0:
                raise ValueError("This book has no available copies.")
            cursor = conn.execute(
                """
                INSERT INTO "Issue" (MemberID, BookID, LibrarianID, IssueDate, ReturnDate)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (member_id, book_id, librarian_id, issue_date),
            )
            conn.execute(
                'UPDATE "Book" SET Available_Copies = Available_Copies - 1 WHERE BookID = ?',
                (book_id,),
            )
            row = conn.execute(issue_select_sql() + " WHERE i.IssueID = ?", (cursor.lastrowid,)).fetchone()
            return issue_from_row(row)

    def return_book(self, issue_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return_date = clean_date(payload.get("return_date") or date.today().isoformat(), "Return date")
        with self._lock, self._connection() as conn:
            issue = conn.execute('SELECT * FROM "Issue" WHERE IssueID = ?', (issue_id,)).fetchone()
            if not issue:
                raise ValueError("Issue record not found.")
            if issue["ReturnDate"]:
                raise ValueError("This book has already been returned.")
            if return_date < issue["IssueDate"]:
                raise ValueError("Return date cannot be before the issue date.")
            conn.execute('UPDATE "Issue" SET ReturnDate = ? WHERE IssueID = ?', (return_date, issue_id))
            conn.execute(
                'UPDATE "Book" SET Available_Copies = Available_Copies + 1 WHERE BookID = ?',
                (issue["BookID"],),
            )
            row = conn.execute(issue_select_sql() + " WHERE i.IssueID = ?", (issue_id,)).fetchone()
            return issue_from_row(row)

    def _delete_row(self, table: str, pk: str, row_id: int, label: str) -> None:
        with self._lock, self._connection() as conn:
            try:
                cursor = conn.execute(f'DELETE FROM "{table}" WHERE {pk} = ?', (row_id,))
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"Cannot delete this {label}; it is linked to issue history.") from exc
            if cursor.rowcount == 0:
                raise ValueError(f"{label.capitalize()} not found.")


def scalar(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> int:
    return int(conn.execute(query, params).fetchone()[0])


def clean_text(value: Any, field: str, max_length: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required.")
    if len(text) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer.")
    return text


def clean_positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is required.") from exc
    if number <= 0:
        raise ValueError(f"{field} is required.")
    return number


def clean_nonnegative_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number.") from exc
    if number < 0:
        raise ValueError(f"{field} cannot be negative.")
    return number


def clean_year(value: Any) -> int:
    try:
        year = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Year must be a number.") from exc
    if year < 1400 or year > 2200:
        raise ValueError("Year must be between 1400 and 2200.")
    return year


def clean_date(value: Any, field: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.strptime(text, DATE_FORMAT)
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD format.") from exc
    return text


def clean_book_payload(payload: dict[str, Any]) -> tuple[str, str, str, int, int]:
    return (
        clean_text(payload.get("title"), "Title", 50),
        clean_text(payload.get("author"), "Author", 50),
        clean_text(payload.get("publisher"), "Publisher", 50),
        clean_year(payload.get("year")),
        clean_nonnegative_int(payload.get("available_copies"), "Available copies"),
    )


def ensure_exists(
    conn: sqlite3.Connection,
    table: str,
    pk: str,
    value: int,
    label: str,
) -> sqlite3.Row:
    row = conn.execute(f'SELECT * FROM "{table}" WHERE {pk} = ?', (value,)).fetchone()
    if not row:
        raise ValueError(f"{label} not found.")
    return row


def member_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "member_id": row["MemberID"],
        "name": row["Name"],
        "address": row["Address"],
        "phone": row["Phone"],
    }


def book_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "book_id": row["BookID"],
        "title": row["Title"],
        "author": row["Author"],
        "publisher": row["Publisher"],
        "year": row["Year"],
        "available_copies": row["Available_Copies"],
    }


def librarian_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "librarian_id": row["LibrarianID"],
        "name": row["Name"],
    }


def issue_from_row(row: sqlite3.Row) -> dict[str, Any]:
    due_date = (datetime.strptime(row["IssueDate"], DATE_FORMAT).date() + timedelta(days=LOAN_DAYS)).isoformat()
    is_active = row["ReturnDate"] is None
    return {
        "issue_id": row["IssueID"],
        "member_id": row["MemberID"],
        "member_name": row["MemberName"],
        "book_id": row["BookID"],
        "book_title": row["BookTitle"],
        "librarian_id": row["LibrarianID"],
        "librarian_name": row["LibrarianName"],
        "issue_date": row["IssueDate"],
        "return_date": row["ReturnDate"],
        "due_date": due_date,
        "status": "Issued" if is_active else "Returned",
        "is_overdue": is_active and due_date < date.today().isoformat(),
    }


def issue_select_sql() -> str:
    return """
        SELECT
            i.IssueID,
            i.MemberID,
            m.Name AS MemberName,
            i.BookID,
            b.Title AS BookTitle,
            i.LibrarianID,
            l.Name AS LibrarianName,
            i.IssueDate,
            i.ReturnDate
        FROM "Issue" i
        JOIN "Member" m ON m.MemberID = i.MemberID
        JOIN "Book" b ON b.BookID = i.BookID
        JOIN "Librarian" l ON l.LibrarianID = i.LibrarianID
    """

