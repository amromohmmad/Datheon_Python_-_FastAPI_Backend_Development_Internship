import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_db():
    main.books_db.clear()
    yield


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_create_and_get():
    r = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "genre": "Sci-Fi"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"]

    r = client.get(f"/books/{body['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Dune"


def test_list_and_filters():
    client.post("/books", json={"title": "Dune", "author": "Herbert", "genre": "Sci-Fi", "year": 1965})
    client.post("/books", json={"title": "Emma", "author": "Austen", "genre": "Classic", "year": 1815})

    assert len(client.get("/books").json()) == 2
    assert [b["title"] for b in client.get("/books", params={"genre": "sci"}).json()] == ["Dune"]
    assert [b["title"] for b in client.get("/books", params={"author": "aust"}).json()] == ["Emma"]
    assert [b["title"] for b in client.get("/books", params={"year": 1965}).json()] == ["Dune"]


def test_update():
    book_id = client.post("/books", json={"title": "Dune", "author": "Herbert"}).json()["id"]

    r = client.put(f"/books/{book_id}", json={"year": 1966})
    assert r.status_code == 200
    assert r.json()["year"] == 1966
    assert r.json()["title"] == "Dune"


def test_delete():
    book_id = client.post("/books", json={"title": "Dune", "author": "Herbert"}).json()["id"]

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_not_found():
    assert client.get("/books/missing").status_code == 404
    assert client.put("/books/missing", json={"title": "X"}).status_code == 404
    assert client.delete("/books/missing").status_code == 404


def test_validation():
    assert client.post("/books", json={"title": ""}).status_code == 422
    assert client.post("/books", json={"title": "X"}).status_code == 422
    assert client.post("/books", json={"title": "X", "author": "Y", "year": 3000}).status_code == 422
