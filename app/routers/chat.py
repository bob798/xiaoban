"""
对话 API：接收用户消息，经 Agent 链路处理后返回回复
"""

import json
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models import ChatSession, ChatMessage
from app.services.agent_service import agent_respond
from app.logger import get_logger

router = APIRouter()
logger = get_logger("chat_router")


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    user_id: str = "default"
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    intent: dict = {}
    plan: dict = {}
    debug: dict = {}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    session_id = req.session_id or uuid.uuid4().hex[:12]
    logger.info("POST /api/chat user=%s session=%s", req.user_id, session_id)

    # 持久化用户消息
    db.add(ChatMessage(session_id=session_id, role="user", content=req.message))
    await db.commit()

    # Agent 链路：意图 → 规划 → 对话
    result = await agent_respond(req.message, req.user_id, req.history)

    # 持久化机器人回复
    db.add(ChatMessage(session_id=session_id, role="assistant", content=result["reply"]))
    await db.commit()

    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        intent=result.get("intent", {}),
        plan=result.get("plan", {}),
        debug=result.get("debug", {}),
    )


@router.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式对话（SSE）——阶段 1 简化版，先完整生成再流式推送"""
    session_id = req.session_id or uuid.uuid4().hex[:12]

    result = await agent_respond(req.message, req.user_id, req.history)

    async def generate():
        # 推送 Agent 调试信息
        yield f"data: {json.dumps({'type': 'agent', 'intent': result['intent'], 'plan': result['plan']}, ensure_ascii=False)}\n\n"

        # 推送回复内容（按句分块模拟流式）
        reply = result["reply"]
        yield f"data: {json.dumps({'type': 'delta', 'content': reply}, ensure_ascii=False)}\n\n"

        # 完成
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        # 异步持久化
        async with AsyncSessionLocal() as db:
            db.add(ChatMessage(session_id=session_id, role="user", content=req.message))
            db.add(ChatMessage(session_id=session_id, role="assistant", content=reply))
            await db.commit()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
