# Datheon Python + FastAPI Backend Development Internship - Task 1

## Book CRUD API

A clean RESTful API built with FastAPI, Pydantic, and Uvicorn. Features:
- CRUD operations (Create, Read, Update, Delete) for books
- Pydantic schemas for request validation
- Query filtering (title, author, genre, year)
- Automatic Swagger UI at `/docs` and ReDoc at `/redoc`
- Proper HTTP status codes and error handling

## Setup

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate it:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Run the API
```bash
uvicorn main:app --reload
```

API will be available at `http://127.0.0.1:8000`

## Endpoints
- `GET /` - Root
- `GET /books` - List all books (supports query filters)
- `GET /books/{id}` - Get book by ID
- `POST /books` - Create new book
- `PUT /books/{id}` - Update book
- `DELETE /books/{id}` - Delete book
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
