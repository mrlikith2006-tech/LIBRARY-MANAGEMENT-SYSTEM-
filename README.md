# Library Management System

A local browser app for managing library members, books, librarians, and issue/return transactions. It follows this schema:

- `Member(MemberID, Name, Address, Phone)`
- `Book(BookID, Title, Author, Publisher, Year, Available_Copies)`
- `Librarian(LibrarianID, Name)`
- `Issue(IssueID, MemberID, BookID, LibrarianID, IssueDate, ReturnDate)`

## Features

- Add, edit, delete, and search members
- Add, edit, delete, and search books
- Add, edit, delete, and search librarians
- Issue books to members through a librarian
- Return books and automatically restore available copy count
- Prevent issuing books when no copies are available
- Preserve issue history through foreign-key relationships
- Dashboard metrics for active issues, overdue records, and available copies
- Schema view matching the database architecture

## Run

Use the batch launcher:

```powershell
.\run_library.bat
```

Or run it directly:

```powershell
python library_app.py --host 127.0.0.1 --port 8010
```

Then open:

```text
http://127.0.0.1:8010
```

Library data is stored locally under:

```text
data/library_management/library.db
```

## Project Structure

```text
.
|-- library_app.py
|-- run_library.bat
|-- run_library.ps1
|-- src/
|   `-- library_management/
|       |-- database.py
|       |-- server.py
|       `-- static/
|           |-- index.html
|           |-- app.js
|           |-- styles.css
|           `-- library-visual.png
`-- tests/
    `-- test_library_management.py
```

## Tests

```powershell
python -m unittest tests.test_library_management
```
