import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from auth.models import User


async def _create_group_and_member(client: AsyncClient) -> tuple[str, str]:
    """Returns (group_id, payer_member_id)."""
    resp = await client.post("/groups", json={"name": "Trip"})
    group_id = resp.json()["id"]
    member_id = resp.json()["members"][0]["id"]
    return group_id, member_id


@pytest.mark.asyncio
async def test_create_expense_equal_split(auth_client: tuple[AsyncClient, User]) -> None:
    client, user = auth_client
    group_id, member_id = await _create_group_and_member(client)
    resp = await client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Dinner",
            "amount": "60.00",
            "currency": "GBP",
            "expense_date": str(date.today()),
            "payer_id": member_id,
            "split_type": "EQUAL",
            "split_details": [{"member_id": member_id}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["split_type"] == "EQUAL"
    assert len(data["splits"]) == 1


@pytest.mark.asyncio
async def test_create_expense_future_date_rejected(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    group_id, member_id = await _create_group_and_member(client)
    future = date.today() + timedelta(days=1)
    resp = await client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Future",
            "amount": "10.00",
            "currency": "GBP",
            "expense_date": str(future),
            "payer_id": member_id,
            "split_type": "EQUAL",
            "split_details": [{"member_id": member_id}],
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_put_expense_returns_405(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    resp = await client.put(f"/groups/{uuid.uuid4()}/expenses/{uuid.uuid4()}")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_delete_expense_returns_405(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    resp = await client.delete(f"/groups/{uuid.uuid4()}/expenses/{uuid.uuid4()}")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_list_expenses_paginated(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    group_id, member_id = await _create_group_and_member(client)
    for i in range(3):
        await client.post(
            f"/groups/{group_id}/expenses",
            json={
                "description": f"Exp {i}",
                "amount": "10.00",
                "currency": "USD",
                "expense_date": str(date.today()),
                "payer_id": member_id,
                "split_type": "EQUAL",
                "split_details": [{"member_id": member_id}],
            },
        )
    resp = await client.get(f"/groups/{group_id}/expenses?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_non_member_cannot_create_expense(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    resp = await client.post(
        f"/groups/{uuid.uuid4()}/expenses",
        json={
            "description": "X",
            "amount": "10.00",
            "currency": "USD",
            "expense_date": str(date.today()),
            "payer_id": str(uuid.uuid4()),
            "split_type": "EQUAL",
            "split_details": [{"member_id": str(uuid.uuid4())}],
        },
    )
    assert resp.status_code == 403
