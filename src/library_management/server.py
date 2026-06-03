from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .database import LibraryDatabase


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "data" / "library_management"
STATIC_DIR = Path(__file__).resolve().parent / "static"


class LibraryHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], database: LibraryDatabase, static_dir: Path) -> None:
        super().__init__(address, RequestHandler)
        self.database = database
        self.static_dir = static_dir


class RequestHandler(BaseHTTPRequestHandler):
    server: LibraryHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self.serve_static("index.html")
            return
        if path == "/api/summary":
            self.send_json({"summary": self.server.database.get_summary()})
            return
        if path == "/api/members":
            self.send_json({"members": self.server.database.list_members()})
            return
        if path == "/api/books":
            self.send_json({"books": self.server.database.list_books()})
            return
        if path == "/api/librarians":
            self.send_json({"librarians": self.server.database.list_librarians()})
            return
        if path == "/api/issues":
            self.send_json({"issues": self.server.database.list_issues()})
            return
        if path.startswith("/static/"):
            self.serve_static(path.removeprefix("/static/"))
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        payload = self.safe_read_json()
        if payload is None:
            return
        try:
            if path == "/api/members":
                self.send_json(
                    {"member": self.server.database.create_member(payload)},
                    status=HTTPStatus.CREATED,
                )
                return
            if path == "/api/books":
                self.send_json(
                    {"book": self.server.database.create_book(payload)},
                    status=HTTPStatus.CREATED,
                )
                return
            if path == "/api/librarians":
                self.send_json(
                    {"librarian": self.server.database.create_librarian(payload)},
                    status=HTTPStatus.CREATED,
                )
                return
            if path == "/api/issues":
                self.send_json(
                    {"issue": self.server.database.issue_book(payload)},
                    status=HTTPStatus.CREATED,
                )
                return
            match = re.fullmatch(r"/api/issues/(\d+)/return", path)
            if match:
                issue_id = int(match.group(1))
                self.send_json({"issue": self.server.database.return_book(issue_id, payload)})
                return
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_PUT(self) -> None:
        path = urlsplit(self.path).path
        payload = self.safe_read_json()
        if payload is None:
            return
        try:
            match = re.fullmatch(r"/api/members/(\d+)", path)
            if match:
                member_id = int(match.group(1))
                self.send_json({"member": self.server.database.update_member(member_id, payload)})
                return
            match = re.fullmatch(r"/api/books/(\d+)", path)
            if match:
                book_id = int(match.group(1))
                self.send_json({"book": self.server.database.update_book(book_id, payload)})
                return
            match = re.fullmatch(r"/api/librarians/(\d+)", path)
            if match:
                librarian_id = int(match.group(1))
                self.send_json({"librarian": self.server.database.update_librarian(librarian_id, payload)})
                return
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_DELETE(self) -> None:
        path = urlsplit(self.path).path
        try:
            match = re.fullmatch(r"/api/members/(\d+)", path)
            if match:
                self.server.database.delete_member(int(match.group(1)))
                self.send_json({"ok": True})
                return
            match = re.fullmatch(r"/api/books/(\d+)", path)
            if match:
                self.server.database.delete_book(int(match.group(1)))
                self.send_json({"ok": True})
                return
            match = re.fullmatch(r"/api/librarians/(\d+)", path)
            if match:
                self.server.database.delete_librarian(int(match.group(1)))
                self.send_json({"ok": True})
                return
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "Route not found.")

    def serve_static(self, relative_path: str) -> None:
        requested = (self.server.static_dir / unquote(relative_path)).resolve()
        static_root = self.server.static_dir.resolve()
        if (
            os.path.commonpath([str(requested), str(static_root)]) != str(static_root)
            or requested.is_dir()
            or not requested.exists()
        ):
            self.send_error_json(HTTPStatus.NOT_FOUND, "Static file not found.")
            return
        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        self.send_bytes(requested.read_bytes(), content_type)

    def safe_read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Invalid request length.")
            return None
        if length > 100_000:
            self.send_error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request is too large.")
            return None
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON.")
            return None
        if not isinstance(payload, dict):
            self.send_error_json(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object.")
            return None
        return payload

    def send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"error": message}, status=status)

    def send_bytes(self, content: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def create_server(host: str, port: int, db_path: Path | str | None = None) -> LibraryHTTPServer:
    database = LibraryDatabase(db_path or DEFAULT_DATA_DIR / "library.db")
    return LibraryHTTPServer((host, port), database, STATIC_DIR)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Library Management System app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", default=8010, type=int, help="Port to serve the app on.")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DATA_DIR / "library.db"),
        help="Path to the SQLite database file.",
    )
    args = parser.parse_args(argv)
    server = create_server(args.host, args.port, Path(args.db))
    print(f"Library Management System running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down library app.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

