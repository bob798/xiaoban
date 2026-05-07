"""
记忆系统：用户画像 + 生活事实 + 知识卡片（FSRS 调度）
"""

import json
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import UserProfile, UserFact, GrammarCard
from app.logger import get_logger

logger = get_logger("memory")


async def get_user_profile(user_id: str) -> dict:
    """获取用户画像，不存在则返回默认值"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return {"occupation": "", "english_level": "B1", "learning_goal": "日常英语"}
        return {
            "occupation": profile.occupation or "",
            "english_level": profile.english_level or "B1",
            "learning_goal": profile.learning_goal or "",
        }


async def update_user_profile(user_id: str, data: dict):
    """更新或创建用户画像"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        for key in ("occupation", "english_level", "learning_goal"):
            if key in data:
                setattr(profile, key, data[key])
        profile.raw_json = json.dumps(data, ensure_ascii=False)
        await db.commit()


async def get_recent_facts(user_id: str, days: int = 7) -> list[str]:
    """获取最近 N 天的用户事实"""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserFact)
            .where(UserFact.user_id == user_id, UserFact.created_at >= cutoff)
            .order_by(UserFact.created_at.desc())
            .limit(10)
        )
        facts = result.scalars().all()
        return [f.content for f in facts]


async def add_user_fact(user_id: str, content: str):
    """添加一条用户事实"""
    async with AsyncSessionLocal() as db:
        db.add(UserFact(user_id=user_id, content=content))
        await db.commit()


async def get_due_cards(user_id: str) -> list[dict]:
    """获取当前到期需要复习的知识卡片"""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(GrammarCard)
            .where(GrammarCard.user_id == user_id, GrammarCard.due <= now)
            .order_by(GrammarCard.difficulty.desc())
            .limit(5)
        )
        cards = result.scalars().all()
        return [
            {
                "id": c.id,
                "key": c.key,
                "description": c.description,
                "difficulty": c.difficulty,
                "due": c.due.isoformat() if c.due else None,
            }
            for c in cards
        ]


async def get_all_cards(user_id: str) -> list[dict]:
    """获取用户的全部知识卡片"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(GrammarCard)
            .where(GrammarCard.user_id == user_id)
            .order_by(GrammarCard.created_at.desc())
        )
        cards = result.scalars().all()
        return [
            {
                "id": c.id,
                "key": c.key,
                "description": c.description,
                "difficulty": c.difficulty,
                "stability": c.stability,
                "reps": c.reps,
                "state": c.state,
                "due": c.due.isoformat() if c.due else None,
            }
            for c in cards
        ]
