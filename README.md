# School Library Management API

A beginner-friendly FastAPI + SQLite project for a school's library. 
## Features

- Choose `Student`, `Professor`, or `Staff` when borrowing a book.
- Automatically save a borrower the first time they borrow; no separate borrower registration is needed.
- Add, edit, and delete books without an admin key (suitable for local demos/testing).
- View books and current available-copy counts.
- Record book/borrower creation dates automatically (date only), and borrowing date.
- Require a due date when borrowing.
- Record the actual return date automatically.
- Prevent borrowing when no copies are available.
- Restore available-copy counts when a book is returned.
- View all borrowing records and overdue records.
- Preserve borrowing history; books with historical loans cannot be deleted.

## Files

- `main.py` — API endpoints.
- `app/database.py` — SQLite connection and table creation.
- `app/models.py` — input validation and database operations.
- `library.db` — created automatically on first startup.

## Run on Windows PowerShell

Open the terminal in this project folder.

1. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

2. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Start the API:

   ```powershell
   python -m uvicorn main:app --reload
   ```

5. Open the interactive API docs at <http://127.0.0.1:8000/docs>.

## Try the API in `/docs`

### 1. Add a book

Use `POST /books` with an example JSON body:

```json
{
  "isbn": "9780131103627",
  "title": "The C Programming Language",
  "author": "Brian W. Kernighan and Dennis W. Ritchie",
  "total_copies": 3
}
```

The API sets `available_copies` to `total_copies` automatically. No admin key is required in this local/demo version.

### 2. Borrow a book

Use `POST /borrow-records`. Enter the borrower's school ID, name, role, book ID, and due date:

```json
{
  "borrower_id": "STU-2026-001",
  "borrower_name": "Alex Santos",
  "borrower_type": "Student",
  "book_id": 1,
  "due_date": "2026-10-18"
}
```

`borrower_type` must be `Student`, `Professor`, or `Staff`. The first time someone borrows, their details are saved automatically. For future borrowing, use the same unique `borrower_id`; the system reuses the existing borrower record. No separate `POST /borrow-records` (borrower details are entered as part of borrowing) step is needed.

`book_id` is the numeric database ID returned when a book is added. The borrowing date is recorded automatically and the available-copy count decreases by one.

### 4. Return a book

Use `POST /borrow-records/1/return`, replacing `1` with the borrow transaction ID. The API records `returned_at`, changes the status to `Returned`, and increases available copies by one.

### Other useful endpoints

- `GET /borrowers`
- `GET /books`
- `GET /books/{book_id}`
- `PUT /books/{book_id}` (single edit endpoint; only fields provided are changed, omitted fields stay unchanged)
- `DELETE /books/{book_id}`
- `GET /borrow-records`
- `GET /borrow-records/overdue`

## Notes and next steps

- This version is an API, not a finished visual website. `/docs` is for development/testing.
- This demo does not require an admin key. Anyone who can access the API can add, edit, or delete books, so add authentication before deploying it publicly.
- Due dates are entered as dates (`YYYY-MM-DD`).

### Update only the fields you want

Use the single `PUT /books/{book_id}` edit endpoint to change only the fields you provide. You do not need to resend every field. For example, to change only the title, send:

```json
{
  "title": "New Book Title"
}
```

The ISBN, author, and copy count remain unchanged. Use `GET /books/{book_id}` first if you want to display the saved/original values in your interface. This project contains an API only. The endpoint preserves omitted fields, but automatically displaying existing values in editable form inputs requires a frontend interface.




