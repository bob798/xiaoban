"""
记忆管理 API：查看/修改用户画像、事实、知识卡片
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.memory_service import (
    get_user_profile, update_user_profile,
    get_recent_facts, add_user_fact,
    get_due_cards, get_all_cards,
)

router = APIRouter(prefix="/api/memory")


class ProfileUpdate(BaseModel):
    occupation: str = ""
    english_level: str = "B1"
    learning_goal: str = ""


class FactCreate(BaseModel):
    content: str


@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    return await get_user_profile(user_id)


@router.put("/profile/{user_id}")
async def put_profile(user_id: str, data: ProfileUpdate):
    await update_user_profile(user_id, data.model_dump())
    return {"ok": True}


@router.get("/facts/{user_id}")
async def get_facts(user_id: str, days: int = 7):
    return await get_recent_facts(user_id, days)


@router.post("/facts/{user_id}")
async def post_fact(user_id: str, data: FactCreate):
    await add_user_fact(user_id, data.content)
    return {"ok": True}


@router.get("/cards/{user_id}")
async def get_cards(user_id: str):
    return await get_all_cards(user_id)


@router.get("/cards/{user_id}/due")
async def get_cards_due(user_id: str):
    return await get_due_cards(user_id)
