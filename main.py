"""API routes for the School Library Management System."""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlite3 import IntegrityError

from app.database import database_connection, initialize_database
from app.models import Borrower, Book, BookInput, BookUpdate, BorrowRecord, BorrowRequest

app = FastAPI(
    title="School Library Management API",
    description=(
        "A beginner-friendly API for managing library books, borrowers, "
        "borrowing transactions, returns, and overdue books."
    ),
    version="1.0.0",
)



@app.get("/")
def home():
    return {
        "message": "Welcome to the School Library Management API.",
        "documentation": "/docs",
    }


@app.get("/borrowers")
def list_borrowers():
    return {"borrowers": Borrower.list_all(database_connection)}


@app.post("/books", status_code=status.HTTP_201_CREATED)
def add_book(book: BookInput):
    try:
        return {"book": Book.create(book, database_connection)}
    except IntegrityError:
        raise HTTPException(status_code=409, detail="That ISBN already exists.")


@app.get("/books")
def list_books():
    return {"books": Book.list_all(database_connection)}


@app.get("/books/{book_id}")
def get_book(book_id: int):
    result = Book.get(book_id, database_connection)
    if result is None:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"book": result}


@app.put("/books/{book_id}")
def edit_book(book_id: int, book: BookUpdate):
    """Single edit endpoint: only provided fields change; omitted fields stay the same."""
    try:
        result = Book.update(book_id, book, database_connection)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="That ISBN already exists.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"book": result}


@app.delete("/books/{book_id}")
def remove_book(book_id: int):
    try:
        deleted = Book.delete(book_id, database_connection)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This book has borrowing history and cannot be deleted. Keep the record instead.",
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found.")
    return {"message": "Book deleted successfully."}


@app.post("/borrow-records", status_code=status.HTTP_201_CREATED)
def borrow_book(request: BorrowRequest):
    try:
        result = BorrowRecord.create(request, database_connection)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"borrow_record": result}


@app.get("/borrow-records")
def list_borrow_records():
    return {"borrow_records": BorrowRecord.list_all(database_connection)}


@app.get("/borrow-records/overdue")
def list_overdue_records():
    return {"overdue_records": BorrowRecord.list_all(database_connection, overdue_only=True)}


@app.post("/borrow-records/{record_id}/return")
def return_book(record_id: int):
    try:
        result = BorrowRecord.return_book(record_id, database_connection)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return {"borrow_record": result}

initialize_database()
