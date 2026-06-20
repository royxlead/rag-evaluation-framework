"""Integration tests for the FastAPI endpoints.

These tests require a running PostgreSQL and Redis instance.
Skip if not available.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

# Check if we should run integration tests
RUN_INTEGRATION = os.environ.get("RAG_EVALUATION_FRAMEWORK_RUN_INTEGRATION", "").lower() == "true"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled by default")
@pytest.mark.asyncio
async def test_health_check():
    """GET /health should return status."""
    from api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "version" in data


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled by default")
@pytest.mark.asyncio
async def test_evaluate_missing_api_key():
    """POST /v1/evaluate without API key should return 401."""
    from api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/evaluate",
            json={
                "question": "Test?",
                "context": ["Context."],
                "answer": "Answer.",
            },
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled by default")
@pytest.mark.asyncio
async def test_evaluate_invalid_api_key():
    """POST /v1/evaluate with invalid API key should return 401."""
    from api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/evaluate",
            json={
                "question": "Test?",
                "context": ["Context."],
                "answer": "Answer.",
            },
            headers={"Authorization": "Bearer reval_invalid_key"},
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled by default")
@pytest.mark.asyncio
async def test_evaluate_missing_fields():
    """POST /v1/evaluate without required fields should return 400."""
    from api.auth import hash_api_key
    from api.database import APIKey, async_session_factory, init_db
    from api.main import app

    # Initialize DB and create test key
    await init_db()
    async with async_session_factory() as session:
        test_key = f"reval_{uuid.uuid4().hex}"
        key_hash = hash_api_key(test_key)
        api_key = APIKey(key_hash=key_hash, name="Test Key")
        session.add(api_key)
        await session.commit()

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/v1/evaluate",
                    json={"context": [], "answer": ""},
                    headers={"Authorization": f"Bearer {test_key}"},
                )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
        finally:
            # Cleanup
            async with async_session_factory() as session:
                await session.delete(api_key)
                await session.commit()


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled by default")
@pytest.mark.asyncio
async def test_batch_invalid_items():
    """POST /v1/batch without items should return 400."""
    from api.auth import hash_api_key
    from api.database import APIKey, async_session_factory
    from api.main import app

    async with async_session_factory() as session:
        test_key = f"reval_{uuid.uuid4().hex}"
        key_hash = hash_api_key(test_key)
        api_key = APIKey(key_hash=key_hash, name="Test Key")
        session.add(api_key)
        await session.commit()

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/v1/batch",
                    json={},
                    headers={"Authorization": f"Bearer {test_key}"},
                )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
        finally:
            async with async_session_factory() as session:
                await session.delete(api_key)
                await session.commit()


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled by default")
@pytest.mark.asyncio
async def test_batch_exceeds_limit():
    """POST /v1/batch with >1000 items should return 400."""
    from api.auth import hash_api_key
    from api.database import APIKey, async_session_factory
    from api.main import app

    async with async_session_factory() as session:
        test_key = f"reval_{uuid.uuid4().hex}"
        key_hash = hash_api_key(test_key)
        api_key = APIKey(key_hash=key_hash, name="Test Key")
        session.add(api_key)
        await session.commit()

        try:
            transport = ASGITransport(app=app)
            items = [{"question": "Q?", "context": ["C"], "answer": "A"} for _ in range(1001)]
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/v1/batch",
                    json={"items": items},
                    headers={"Authorization": f"Bearer {test_key}"},
                )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
        finally:
            async with async_session_factory() as session:
                key = await session.get(APIKey, uuid.UUID(test_key))
                if key:
                    await session.delete(key)
                    await session.commit()
