import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models import User

USERNAME = "testuser"
PASSWORD = "secret123"


def register_and_login(client, username=USERNAME, password=PASSWORD):
    client.post("/register", json={"username": username, "password": password})
    response = client.post("/login", data={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client):
    return register_and_login(client)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_register_login_and_me(client):
    r = client.post("/register", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 201
    assert r.json()["username"] == USERNAME
    assert "password" not in r.json()
    assert "hashed_password" not in r.json()

    r = client.post("/login", data={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    r = client.get("/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200
    assert r.json()["username"] == USERNAME


def test_register_duplicate_username(client):
    client.post("/register", json={"username": USERNAME, "password": PASSWORD})
    r = client.post("/register", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 409


def test_login_wrong_password(client):
    client.post("/register", json={"username": USERNAME, "password": PASSWORD})
    r = client.post("/login", data={"username": USERNAME, "password": "wrongpass"})
    assert r.status_code == 401


def test_password_is_hashed(client):
    client.post("/register", json={"username": USERNAME, "password": PASSWORD})

    async def fetch_hash():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.username == USERNAME))
            return result.scalar_one().hashed_password

    stored = client.portal.call(fetch_hash)
    assert stored != PASSWORD
    assert stored.startswith("$2")


def test_protected_routes_require_auth(client):
    assert client.post("/books", json={"title": "Dune", "author": "Herbert"}).status_code == 401
    assert client.put("/books/missing", json={"title": "X"}).status_code == 401
    assert client.delete("/books/missing").status_code == 401
    assert client.get("/me").status_code == 401


def test_invalid_token_rejected(client):
    headers = {"Authorization": "Bearer not-a-real-token"}
    r = client.post("/books", json={"title": "Dune", "author": "Herbert"}, headers=headers)
    assert r.status_code == 401


def test_create_and_get(client, auth_headers):
    r = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "genre": "Sci-Fi"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"]
    assert body["owner_id"]

    r = client.get(f"/books/{body['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Dune"


def test_user_books_relationship(client, auth_headers):
    client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "genre": "Sci-Fi", "year": 1965},
        headers=auth_headers,
    )

    async def fetch_user_with_books():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).options(selectinload(User.books)).where(User.username == USERNAME)
            )
            user = result.scalar_one()
            return [(book.title, book.owner_id) for book in user.books]

    books = client.portal.call(fetch_user_with_books)
    assert books == [("Dune", client.get("/me", headers=auth_headers).json()["id"])]


def test_list_and_filters(client, auth_headers):
    client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "genre": "Sci-Fi", "year": 1965},
        headers=auth_headers,
    )
    client.post(
        "/books",
        json={"title": "Emma", "author": "Austen", "genre": "Classic", "year": 1815},
        headers=auth_headers,
    )

    assert len(client.get("/books").json()) == 2
    assert [b["title"] for b in client.get("/books", params={"genre": "sci"}).json()] == ["Dune"]
    assert [b["title"] for b in client.get("/books", params={"author": "aust"}).json()] == ["Emma"]
    assert [b["title"] for b in client.get("/books", params={"year": 1965}).json()] == ["Dune"]


def test_update(client, auth_headers):
    book_id = client.post(
        "/books", json={"title": "Dune", "author": "Herbert"}, headers=auth_headers
    ).json()["id"]

    r = client.put(f"/books/{book_id}", json={"year": 1966}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["year"] == 1966
    assert r.json()["title"] == "Dune"


def test_delete(client, auth_headers):
    book_id = client.post(
        "/books", json={"title": "Dune", "author": "Herbert"}, headers=auth_headers
    ).json()["id"]

    assert client.delete(f"/books/{book_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_not_found(client, auth_headers):
    assert client.get("/books/missing").status_code == 404
    assert client.put("/books/missing", json={"title": "X"}, headers=auth_headers).status_code == 404
    assert client.delete("/books/missing", headers=auth_headers).status_code == 404


def test_validation(client, auth_headers):
    assert client.post("/books", json={"title": ""}, headers=auth_headers).status_code == 422
    assert client.post("/books", json={"title": "X"}, headers=auth_headers).status_code == 422
    assert (
        client.post(
            "/books",
            json={"title": "X", "author": "Y", "year": 3000},
            headers=auth_headers,
        ).status_code
        == 422
    )


def test_book_ownership_enforced(client, auth_headers):
    book_id = client.post(
        "/books", json={"title": "Dune", "author": "Herbert"}, headers=auth_headers
    ).json()["id"]

    other_headers = register_and_login(client, username="otheruser", password="otherpass123")

    r = client.put(f"/books/{book_id}", json={"title": "Hijacked"}, headers=other_headers)
    assert r.status_code == 403

    r = client.delete(f"/books/{book_id}", headers=other_headers)
    assert r.status_code == 403

    assert client.get(f"/books/{book_id}").json()["title"] == "Dune"
