from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, init_db
from models import Book, User
from schemas import (
    BookCreate,
    BookRead,
    BookUpdate,
    Token,
    UserCreate,
    UserRead,
)
from security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Book CRUD API",
    description="Datheon Python + FastAPI Backend Development - Async SQLAlchemy + JWT",
    version="3.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Book CRUD API", "docs": "/docs"}


@app.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.username == user.username))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    db_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    await db.refresh(db_user)
    return db_user


@app.post("/login", response_model=Token, tags=["Auth"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=UserRead, tags=["Auth"])
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/books", response_model=List[BookRead], tags=["Books"])
async def get_books(
    title: Optional[str] = Query(None, description="Filter by title (case-insensitive contains)"),
    author: Optional[str] = Query(None, description="Filter by author (case-insensitive contains)"),
    genre: Optional[str] = Query(None, description="Filter by genre (case-insensitive contains)"),
    year: Optional[int] = Query(None, description="Filter by exact year"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Book)
    if title:
        stmt = stmt.where(Book.title.ilike(f"%{title}%"))
    if author:
        stmt = stmt.where(Book.author.ilike(f"%{author}%"))
    if genre:
        stmt = stmt.where(Book.genre.ilike(f"%{genre}%"))
    if year is not None:
        stmt = stmt.where(Book.year == year)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@app.get("/books/{book_id}", response_model=BookRead, tags=["Books"])
async def get_book(book_id: str, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.post(
    "/books",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Books"],
)
async def create_book(
    book: BookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_book = Book(**book.model_dump(), owner_id=current_user.id)
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book


@app.put("/books/{book_id}", response_model=BookRead, tags=["Books"])
async def update_book(
    book_id: str,
    book_update: BookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this book",
        )

    for field, value in book_update.model_dump(exclude_unset=True).items():
        setattr(book, field, value)

    await db.commit()
    await db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Books"])
async def delete_book(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this book",
        )

    await db.delete(book)
    await db.commit()
    return None
