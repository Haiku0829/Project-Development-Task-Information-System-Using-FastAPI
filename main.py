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


@app.get("/manage-books", response_class=HTMLResponse, include_in_schema=False)
def manage_books_page():
    """Small UI that fetches a book by ID first, then lets the user edit it."""
    return HTMLResponse(r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manage Books | School Library</title>
<style>
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#172033;background:#f4f7fb}*{box-sizing:border-box}body{margin:0;padding:28px 16px}.wrap{max-width:850px;margin:auto}.panel{background:white;border:1px solid #e1e7ef;border-radius:16px;padding:24px;margin:18px 0;box-shadow:0 8px 24px #182b4910}h1{margin:0 0 8px}p{color:#5e6a7d}.row{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.field{display:flex;flex-direction:column;gap:6px;flex:1;min-width:180px;margin:10px 0}label{font-size:14px;font-weight:650}input{font:inherit;padding:11px 12px;border:1px solid #cbd5e1;border-radius:9px;width:100%}input:disabled{background:#f1f5f9;color:#64748b}button{font:inherit;font-weight:650;padding:11px 16px;border:0;border-radius:9px;background:#2457d6;color:white;cursor:pointer}button.secondary{background:#e8eefb;color:#2045a0}button:disabled{opacity:.45;cursor:not-allowed}.status{padding:12px;border-radius:9px;background:#f1f5f9;margin-top:14px;white-space:pre-wrap}.status.error{background:#fff0f0;color:#9f2020}.status.success{background:#eaf8ef;color:#176637}.meta{font-size:13px;color:#64748b}a{color:#2457d6}
</style></head><body><main class="wrap"><p class="meta">SCHOOL LIBRARY MANAGEMENT SYSTEM</p><h1>Update a book</h1><p>First retrieve the book by ID. Review its current details, edit the fields you want, then save.</p>
<section class="panel"><h2>1. Find existing book</h2><div class="row"><div class="field"><label for="bookId">Book ID</label><input id="bookId" type="number" min="1" step="1" placeholder="Enter book ID, e.g. 3"></div><button id="loadBtn" type="button">Get book details</button></div><div id="lookupStatus" class="status" role="status">Enter an existing book ID to load its information.</div></section>
<section class="panel"><h2>2. Edit book details</h2><p class="meta" id="loadedMeta">Load a book first. Existing values will appear here.</p><form id="editForm"><div class="field"><label for="isbn">ISBN (permanent; cannot be changed)</label><input id="isbn" maxlength="30" disabled readonly></div><div class="field"><label for="title">Title</label><input id="title" maxlength="250" required disabled></div><div class="field"><label for="author">Author</label><input id="author" maxlength="150" required disabled></div><div class="field"><label for="totalCopies">Total copies</label><input id="totalCopies" type="number" min="1" step="1" required disabled></div><p class="meta" id="availability"></p><button id="saveBtn" type="submit" disabled>Save changes</button> <button id="resetBtn" class="secondary" type="button" disabled>Reload original values</button></form><div id="saveStatus" class="status" role="status">No book loaded yet.</div></section><p class="meta"><a href="/docs">Open API documentation</a> · <a href="/books">View books JSON</a></p></main>
<script>
const $=id=>document.getElementById(id);let loadedBook=null;
function status(id,msg,type=''){const el=$(id);el.textContent=msg;el.className='status'+(type?' '+type:'')}
function formEnabled(on){['isbn','title','author','totalCopies','saveBtn','resetBtn'].forEach(id=>$(id).disabled=!on)}
function fill(book){loadedBook=book;$('isbn').value=book.isbn??'';$('title').value=book.title??'';$('author').value=book.author??'';$('totalCopies').value=book.total_copies;$('loadedMeta').textContent=`Loaded book ID ${book.id} · Created ${book.created_at??'date unavailable'}`;$('availability').textContent=`Currently available: ${book.available_copies} of ${book.total_copies} copies` ;formEnabled(true);status('saveStatus','Ready to edit. Only changed fields will be sent.')}
async function readResponse(res){let data;try{data=await res.json()}catch{throw new Error(`Server returned HTTP ${res.status}`)}if(!res.ok)throw new Error(data.detail||`Request failed (${res.status})`);return data}
$('loadBtn').addEventListener('click',async()=>{const id=$('bookId').value;if(!id||Number(id)<1){status('lookupStatus','Please enter a valid book ID.','error');return} $('loadBtn').disabled=true;status('lookupStatus','Loading book information…');try{const data=await readResponse(await fetch(`/books/${encodeURIComponent(id)}`));fill(data.book);status('lookupStatus',`Book ID ${data.book.id} found. Review the information below before updating.`,'success')}catch(e){loadedBook=null;formEnabled(false);status('lookupStatus',e.message,'error')}finally{$('loadBtn').disabled=false}});
$('resetBtn').addEventListener('click',()=>{if(loadedBook)fill(loadedBook)});
$('editForm').addEventListener('submit',async event=>{event.preventDefault();if(!loadedBook)return;const body={};const isbn=$('isbn').value.trim(),title=$('title').value.trim(),author=$('author').value.trim(),copies=Number($('totalCopies').value);if(title!==loadedBook.title)body.title=title;if(author!==loadedBook.author)body.author=author;if(copies!==loadedBook.total_copies)body.total_copies=copies;// ISBN is immutable and is deliberately not sent in update requests.if(!Object.keys(body).length){status('saveStatus','No changes detected. Edit at least one field before saving.');return} $('saveBtn').disabled=true;status('saveStatus','Saving changes…');try{const data=await readResponse(await fetch(`/books/${loadedBook.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}));fill(data.book);status('saveStatus',`Book ID ${data.book.id} updated successfully.`,'success');status('lookupStatus','Update complete. You can edit more fields or load another book.','success')}catch(e){status('saveStatus',e.message,'error')}finally{$('saveBtn').disabled=false}});
$('bookId').addEventListener('keydown',e=>{if(e.key==='Enter'){$('loadBtn').click()}});
</script></body></html>''')


initialize_database()
