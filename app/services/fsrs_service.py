from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.logger import get_logger
from app.models import GrammarCard

logger = get_logger("fsrs_service")

_scheduler = Scheduler()

_RATING_MAP = {
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Good,
    4: Rating.Easy,
}

_STATE_VALUE = {
    State.Learning: 1,
    State.Review: 2,
    State.Relearning: 3,
}


async def review_card(user_id: str, card_id: int, rating: int) -> dict:
    rating_enum = _RATING_MAP.get(rating, Rating.Good)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(GrammarCard).where(
                GrammarCard.id == card_id, GrammarCard.user_id == user_id
            )
        )
        card_row = result.scalar_one_or_none()
        if not card_row:
            return {"ok": False, "error": "card not found"}

        state_map = {0: None, 1: State.Learning, 2: State.Review, 3: State.Relearning}
        current_state = state_map.get(card_row.state)

        fsrs_card = Card(
            stability=card_row.stability if card_row.stability else None,
            difficulty=card_row.difficulty if card_row.difficulty else None,
            due=card_row.due.replace(tzinfo=timezone.utc) if card_row.due else datetime.now(timezone.utc),
            last_review=card_row.last_review.replace(tzinfo=timezone.utc) if card_row.last_review else None,
            state=current_state if current_state else State.Learning,
        )

        updated_card, _ = _scheduler.review_card(fsrs_card, rating_enum)

        card_row.due = updated_card.due.replace(tzinfo=None)
        card_row.stability = updated_card.stability
        card_row.difficulty = updated_card.difficulty
        card_row.state = _STATE_VALUE.get(updated_card.state, 1)
        card_row.last_review = (updated_card.last_review.replace(tzinfo=None)
                                if updated_card.last_review else datetime.utcnow())
        if rating_enum == Rating.Again:
            card_row.lapses += 1
        card_row.reps += 1

        await db.commit()

        logger.info("review_card user=%s card=%s rating=%s due=%s",
                    user_id, card_id, rating, card_row.due)
        return {
            "ok": True,
            "due": card_row.due.isoformat(),
            "stability": card_row.stability,
            "difficulty": card_row.difficulty,
            "state": card_row.state,
            "reps": card_row.reps,
        }


async def create_card(user_id: str, key: str, description: str) -> dict:
    async with AsyncSessionLocal() as db:
        card = GrammarCard(
            user_id=user_id,
            key=key,
            description=description,
            state=0,
            due=datetime.utcnow(),
            stability=0.0,
            difficulty=0.0,
            reps=0,
            lapses=0,
        )
        db.add(card)
        await db.commit()
        await db.refresh(card)
        logger.info("create_card user=%s key=%s id=%s", user_id, key, card.id)
        return {"ok": True, "id": card.id, "key": key}
