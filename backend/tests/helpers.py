"""Shared HTTP helpers for API tests."""

from fastapi.testclient import TestClient

from app.services.llm import ModelUnreachable


def register(client: TestClient, email: str = "ada@example.com", password: str = "correct-horse") -> dict:
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def unreachable() -> ModelUnreachable:
    return ModelUnreachable("connection refused")
