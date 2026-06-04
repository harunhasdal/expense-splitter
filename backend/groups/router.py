import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.models import User
from core.db import get_db
from groups import service as group_service
from groups.schemas import AddMemberRequest, GroupCreate, GroupResponse, GroupUpdate, MemberResponse

router = APIRouter()


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    body: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    group = await group_service.create_group(db, current_user, body.name, body.description)
    return GroupResponse.model_validate(group)


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupResponse]:
    groups = await group_service.list_groups(db, current_user.id, include_archived)
    return [GroupResponse.model_validate(g) for g in groups]


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    group = await group_service.get_group(db, group_id, current_user.id)
    return GroupResponse.model_validate(group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    body: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupResponse:
    if body.archived:
        group = await group_service.archive_group(db, group_id, current_user, force=body.force)
    else:
        group = await group_service.get_group(db, group_id, current_user.id)
        from groups import repository as group_repo
        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.description is not None:
            updates["description"] = body.description
        if updates:
            async with db.begin():
                await group_repo.update_group(db, group, **updates)
    return GroupResponse.model_validate(group)


@router.post("/{group_id}/members", response_model=MemberResponse, status_code=201)
async def add_member(
    group_id: uuid.UUID,
    body: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    member = await group_service.add_member(db, group_id, current_user, str(body.email))
    return MemberResponse.model_validate(member)


@router.delete("/{group_id}/members/{member_id}", status_code=200)
async def remove_member(
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await group_service.remove_member(db, group_id, member_id, current_user)
    return {"message": "Member removed"}
