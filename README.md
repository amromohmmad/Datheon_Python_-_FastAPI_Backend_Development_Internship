# Datheon Python + FastAPI Backend Development

## Book CRUD API with Async SQLAlchemy and JWT Authentication

A RESTful API built with FastAPI, async SQLAlchemy 2.0, SQLite (`aiosqlite`), and
JWT authentication. Users own books through a relational one-to-many model.

## Features

- Async SQLAlchemy ORM with async sessions and dependency injection
- SQLite by default (`sqlite+aiosqlite`), configurable for PostgreSQL
- Relational models: `User` (one) -> `Book` (many)
- Ownership enforcement: only a book's owner can update or delete it
- User registration and login with bcrypt-hashed passwords
- Signed, expiring JWT access tokens (`python-jose`, HS256)
- OAuth2 Password Bearer scheme with Swagger UI integration
- CRUD operations with Pydantic request/response schemas
- Query filtering (title, author, genre, year)
- Automatic Swagger UI at `/docs` and ReDoc at `/redoc`
- Async test suite using an isolated in-memory database

## Project structure

```
database.py   # async engine, sessionmaker, Base, get_db, init_db
models.py     # SQLAlchemy declarative models: User -> Book
schemas.py    # Pydantic request/response DTOs
security.py   # password hashing, JWT creation/verification, get_current_user
main.py       # FastAPI app, lifespan, endpoints
tests/        # pytest suite with in-memory DB
```

## Architecture

```
Request
  -> FastAPI dependency get_db()             (database.py)
  -> AsyncSession                            (SQLAlchemy)
  -> Endpoint handler                        (main.py)
  -> ORM model queries / commits             (models.py)
  -> Pydantic response model serialization   (schemas.py)
```

`get_db` yields one `AsyncSession` per request and closes it automatically. FastAPI
caches the dependency within a request, so `get_current_user` and the endpoint share
the same session.

## Setup

1. Create a virtual environment:
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

4. (Optional) Configure the database and token settings:
```bash
set DATABASE_URL=sqlite+aiosqlite:///./books.db
set SECRET_KEY=your-secret-key
set ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Defaults:
- `DATABASE_URL=sqlite+aiosqlite:///./books.db`
- `SECRET_KEY=dev-only-change-me-in-production` (must be overridden in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES=30`

### PostgreSQL

Install the async driver and point `DATABASE_URL` at it:

```bash
pip install asyncpg
set DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/books
```

Tables are created automatically on application startup. For production schema
changes, add Alembic migrations.

## Run the API

```bash
uvicorn main:app --reload
```

API will be available at `http://127.0.0.1:8000`.

## Endpoints

### Auth
- `POST /register` - Register a user (`username`, `password`) - returns `201`
- `POST /login` - Login with form data (`username`, `password`) and receive a JWT
- `GET /me` - Get the authenticated user (requires token)

### Books
- `GET /` - Root
- `GET /books` - List all books (supports query filters)
- `GET /books/{id}` - Get book by ID
- `POST /books` - Create a book owned by the current user (requires token)
- `PUT /books/{id}` - Update a book (requires token + ownership)
- `DELETE /books/{id}` - Delete a book (requires token + ownership)
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

## Authentication flow

Register, then log in to get a token:

```bash
curl -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"alice\", \"password\": \"secret123\"}"

curl -X POST http://127.0.0.1:8000/login \
  -d "username=alice&password=secret123"
```

Use the returned `access_token` in the `Authorization` header for protected routes:

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Dune\", \"author\": \"Frank Herbert\", \"year\": 1965}"
```

The created `Book` includes `owner_id`, linking it to the authenticated user.

## Ownership rules

- Reads (`GET /books`, `GET /books/{id}`) are public.
- Writes require a valid JWT.
- `PUT` and `DELETE` return `403 Forbidden` when the authenticated user is not the
  book's owner.
- Deleting a user cascades to their books at the ORM level.

## Tests

Tests run against an isolated in-memory SQLite database and reset state between
tests:

```bash
pytest
```
