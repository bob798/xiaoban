from fastapi import APIRouter
from pydantic import BaseModel

from app.services.fsrs_service import create_card, review_card

router = APIRouter(prefix="/api/cards")


class CardCreate(BaseModel):
    key: str
    description: str = ""


class CardReview(BaseModel):
    rating: int


@router.post("/{user_id}")
async def post_create_card(user_id: str, data: CardCreate):
    return await create_card(user_id, data.key, data.description)


@router.post("/{user_id}/{card_id}/review")
async def post_review_card(user_id: str, card_id: int, data: CardReview):
    return await review_card(user_id, card_id, data.rating)
