import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from auth.models import User


async def _setup_group_two_members(
    client: AsyncClient,
) -> tuple[str, str, str]:
    """Returns (group_id, member1_id, member2_id). member2 is a pending member."""
    resp = await client.post("/groups", json={"name": "Settle Test"})
    group_id = resp.json()["id"]
    member1_id = resp.json()["members"][0]["id"]
    m2_resp = await client.post(f"/groups/{group_id}/members", json={"email": "bob@example.com"})
    member2_id = m2_resp.json()["id"]
    return group_id, member1_id, member2_id


@pytest.mark.asyncio
async def test_create_settlement(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    group_id, m1, m2 = await _setup_group_two_members(client)
    resp = await client.post(
        f"/groups/{group_id}/settlements",
        json={"payer_id": m1, "payee_id": m2, "amount": "30.00", "currency": "GBP"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["payer_id"] == m1
    assert data["payee_id"] == m2


@pytest.mark.asyncio
async def test_zero_amount_settlement_rejected(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    group_id, m1, m2 = await _setup_group_two_members(client)
    resp = await client.post(
        f"/groups/{group_id}/settlements",
        json={"payer_id": m1, "payee_id": m2, "amount": "0", "currency": "GBP"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_self_settlement_rejected(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    group_id, m1, _ = await _setup_group_two_members(client)
    resp = await client.post(
        f"/groups/{group_id}/settlements",
        json={"payer_id": m1, "payee_id": m1, "amount": "10.00", "currency": "GBP"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_non_member_cannot_settle(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    resp = await client.post(
        f"/groups/{uuid.uuid4()}/settlements",
        json={
            "payer_id": str(uuid.uuid4()),
            "payee_id": str(uuid.uuid4()),
            "amount": "10.00",
            "currency": "GBP",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_settlements(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    group_id, m1, m2 = await _setup_group_two_members(client)
    await client.post(
        f"/groups/{group_id}/settlements",
        json={"payer_id": m1, "payee_id": m2, "amount": "20.00", "currency": "EUR"},
    )
    resp = await client.get(f"/groups/{group_id}/settlements")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
