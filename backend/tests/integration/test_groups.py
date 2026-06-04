import pytest
from httpx import AsyncClient

from auth.models import User


@pytest.mark.asyncio
async def test_create_group(auth_client: tuple[AsyncClient, User]) -> None:
    client, user = auth_client
    resp = await client.post("/groups", json={"name": "Greece Trip"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Greece Trip"
    assert data["owner_id"] == str(user.id)
    assert len(data["members"]) == 1


@pytest.mark.asyncio
async def test_create_group_name_too_long(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    resp = await client.post("/groups", json={"name": "x" * 101})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_groups(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    await client.post("/groups", json={"name": "Group A"})
    await client.post("/groups", json={"name": "Group B"})
    resp = await client.get("/groups")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_group_not_member_returns_404(auth_client: tuple[AsyncClient, User]) -> None:
    import uuid
    client, _ = auth_client
    resp = await client.get(f"/groups/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_pending_member(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    create_resp = await client.post("/groups", json={"name": "Flat"})
    group_id = create_resp.json()["id"]
    resp = await client.post(f"/groups/{group_id}/members", json={"email": "new@example.com"})
    assert resp.status_code == 201
    assert resp.json()["is_pending"] is True


@pytest.mark.asyncio
async def test_add_duplicate_member_returns_409(auth_client: tuple[AsyncClient, User]) -> None:
    client, user = auth_client
    create_resp = await client.post("/groups", json={"name": "Flat"})
    group_id = create_resp.json()["id"]
    await client.post(f"/groups/{group_id}/members", json={"email": "dup@example.com"})
    resp = await client.post(f"/groups/{group_id}/members", json={"email": "dup@example.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_archive_group_no_balances(auth_client: tuple[AsyncClient, User]) -> None:
    client, _ = auth_client
    create_resp = await client.post("/groups", json={"name": "Done"})
    group_id = create_resp.json()["id"]
    resp = await client.patch(f"/groups/{group_id}", json={"archived": True})
    assert resp.status_code == 200
    assert resp.json()["archived_at"] is not None
