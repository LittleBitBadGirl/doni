"""Integration tests for health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_should_return_ok_from_health(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
