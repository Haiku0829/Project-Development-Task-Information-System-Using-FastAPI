"""Pydantic input models and SQLite operations for the library system."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.database import current_date, current_timestamp


BorrowerType = Literal["Student", "Professor", "Staff"]


class BorrowerInput(BaseModel):
    borrower_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    borrower_type: BorrowerType

    @field_validator("borrower_id", "name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class BookInput(BaseModel):
    isbn: str | None = Field(default=None, max_length=30)
    title: str = Field(min_length=1, max_length=250)
    author: str = Field(min_length=1, max_length=150)
    total_copies: int = Field(ge=1)

    @field_validator("isbn", "title", "author")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BorrowRequest(BaseModel):
    borrower_id: str = Field(min_length=1, max_length=50)
    borrower_name: str = Field(min_length=1, max_length=150)
    borrower_type: BorrowerType
    book_id: int = Field(ge=1)
    due_date: date

    @field_validator("borrower_id", "borrower_name")
    @classmethod
    def strip_borrower_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class Borrower:
    @staticmethod
    def list_all(database_connection):
        with database_connection() as connection:
            rows = connection.execute(
                "SELECT id, borrower_id, name, borrower_type, created_at "
                "FROM borrowers ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(data: BorrowerInput, database_connection):
        with database_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO borrowers (borrower_id, name, borrower_type, created_at) "
                "VALUES (?, ?, ?, ?)",
                (data.borrower_id, data.name, data.borrower_type, current_date()),
            )
            row = connection.execute(
                "SELECT id, borrower_id, name, borrower_type, created_at "
                "FROM borrowers WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)


class BookUpdate(BaseModel):
    # ISBN identifies the book and is intentionally immutable after creation.
    title: str | None = Field(default=None, min_length=1, max_length=250)
    author: str | None = Field(default=None, min_length=1, max_length=150)
    total_copies: int | None = Field(default=None, ge=1)

    @field_validator("title", "author")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class Book:
    @staticmethod
    def list_all(database_connection):
        with database_connection() as connection:
            rows = connection.execute(
                "SELECT id, isbn, title, author, total_copies, available_copies, created_at "
                "FROM books ORDER BY title"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get(book_id: int, database_connection):
        with database_connection() as connection:
            row = connection.execute(
                "SELECT id, isbn, title, author, total_copies, available_copies, created_at "
                "FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(data: BookInput, database_connection):
        with database_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO books (isbn, title, author, total_copies, available_copies, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (data.isbn or None, data.title.strip(), data.author.strip(), data.total_copies,
                 data.total_copies, current_date()),
            )
            row = connection.execute(
                "SELECT id, isbn, title, author, total_copies, available_copies, created_at "
                "FROM books WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return dict(row)

    @staticmethod
    def update(book_id: int, data: BookUpdate, database_connection):
        with database_connection() as connection:
            current = connection.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if current is None:
                return None

            # ISBN is permanent after creation; never accept it as an update field.
            isbn = current["isbn"]
            title = data.title if data.title is not None else current["title"]
            author = data.author if data.author is not None else current["author"]
            total_copies = data.total_copies if data.total_copies is not None else current["total_copies"]
            borrowed_copies = current["total_copies"] - current["available_copies"]
            if total_copies < borrowed_copies:
                raise ValueError(
                    f"Cannot set total_copies below {borrowed_copies}; that many copies are currently borrowed."
                )

            connection.execute(
                "UPDATE books SET isbn = ?, title = ?, author = ?, total_copies = ?, available_copies = ? WHERE id = ?",
                (isbn, title.strip(), author.strip(), total_copies,
                 total_copies - borrowed_copies, book_id),
            )
            row = connection.execute(
                "SELECT id, isbn, title, author, total_copies, available_copies, created_at "
                "FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        return dict(row)

    @staticmethod
    def delete(book_id: int, database_connection):
        with database_connection() as connection:
            exists = connection.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
            if exists is None:
                return False
            history = connection.execute(
                "SELECT COUNT(*) AS count FROM borrow_records WHERE book_id = ?", (book_id,)
            ).fetchone()["count"]
            if history:
                raise ValueError("This book has borrowing history and cannot be deleted. Keep the record instead.")
            cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return cursor.rowcount > 0

class BorrowRecord:
    @staticmethod
    def list_all(database_connection, overdue_only: bool = False):
        sql = """
            SELECT br.id, b.borrower_id, b.name AS borrower_name,
            b.borrower_type, bk.id AS book_id, bk.title AS book_title,
            br.borrowed_at, br.due_date, br.returned_at, br.status
            FROM borrow_records br
            JOIN borrowers b ON b.id = br.borrower_record_id
            JOIN books bk ON bk.id = br.book_id
        """
        params: tuple = ()
        if overdue_only:
            sql += " WHERE br.status = 'Borrowed' AND br.due_date < date('now', 'localtime')"
        sql += " ORDER BY br.borrowed_at DESC"
        with database_connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(data: BorrowRequest, database_connection):
        with database_connection() as connection:
            # Automatically save a borrower's details the first time they borrow.
            # Returning borrowers are matched by their unique school ID.
            borrower = connection.execute(
                "SELECT id, name, borrower_type FROM borrowers WHERE borrower_id = ?",
                (data.borrower_id,),
            ).fetchone()
            if borrower is None:
                cursor = connection.execute(
                    "INSERT INTO borrowers (borrower_id, name, borrower_type, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (data.borrower_id, data.borrower_name, data.borrower_type, current_date()),
                )
                borrower_record_id = cursor.lastrowid
            else:
                borrower_record_id = borrower["id"]

            book = connection.execute(
                "SELECT id, available_copies FROM books WHERE id = ?", (data.book_id,)
            ).fetchone()
            if book is None:
                raise LookupError("Book was not found.")
            if book["available_copies"] < 1:
                raise ValueError("No copies of this book are currently available.")
            if data.due_date < date.today():
                raise ValueError("The due date cannot be in the past.")

            connection.execute(
                "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
                (data.book_id,),
            )
            cursor = connection.execute(
                "INSERT INTO borrow_records "
                "(borrower_record_id, book_id, borrowed_at, due_date, status) "
                "VALUES (?, ?, ?, ?, 'Borrowed')",
                (borrower_record_id, data.book_id, current_timestamp(), data.due_date.isoformat()),
            )
            row = connection.execute(
                """
                SELECT br.id, b.borrower_id, b.name AS borrower_name,
                       b.borrower_type, bk.id AS book_id, bk.title AS book_title,
                       br.borrowed_at, br.due_date, br.returned_at, br.status
                FROM borrow_records br
                JOIN borrowers b ON b.id = br.borrower_record_id
                JOIN books bk ON bk.id = br.book_id
                WHERE br.id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)

    @staticmethod
    def return_book(record_id: int, database_connection):
        with database_connection() as connection:
            record = connection.execute(
                "SELECT book_id, status FROM borrow_records WHERE id = ?", (record_id,)
            ).fetchone()
            if record is None:
                raise LookupError("Borrowing record was not found.")
            if record["status"] == "Returned":
                raise ValueError("This book has already been returned.")

            connection.execute(
                "UPDATE borrow_records SET returned_at = ?, status = 'Returned' WHERE id = ?",
                (current_timestamp(), record_id),
            )
            connection.execute(
                "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
                (record["book_id"],),
            )
            row = connection.execute(
                """
                SELECT br.id, b.borrower_id, b.name AS borrower_name,
                       b.borrower_type, bk.id AS book_id, bk.title AS book_title,
                       br.borrowed_at, br.due_date, br.returned_at, br.status
                FROM borrow_records br
                JOIN borrowers b ON b.id = br.borrower_record_id
                JOIN books bk ON bk.id = br.book_id
                WHERE br.id = ?
                """,
                (record_id,),
            ).fetchone()
        return dict(row)
