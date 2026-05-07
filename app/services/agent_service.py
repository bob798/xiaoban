"""
Agent 决策层：意图理解 → 任务规划 → 对话执行

文心大模型 × 3 次调用构成的 Agent 链路。
"""

import json
from app.services import ernie_client
from app.services.memory_service import get_user_profile, get_recent_facts, get_due_cards
from app.logger import get_logger

logger = get_logger("agent")

# ── 调用点 1：意图识别 ────────────────────────────

INTENT_SYSTEM_PROMPT = """你是学习机器人"小伴"的意图分类器。
根据用户输入，返回 JSON 格式的意图分类结果。

可用意图：
- practice: 开始新的练习对话（关键词：练习、学习、开始、today、练、聊）
- review: 复习之前的错误或知识点（关键词：复习、回顾、错误、上次、review）
- summary: 总结学习情况（关键词：总结、报告、这周、进步、summary）
- freeChat: 自由聊天（不属于以上三类的日常对话）

返回严格 JSON，不要输出其他内容：
{"intent": "practice|review|summary|freeChat", "params": {}, "confidence": 0.0-1.0}"""


async def classify_intent(user_text: str) -> dict:
    """调用点 1：意图理解（temperature=0.1，确定性分类）"""
    messages = [
        {"role": "system", "content": INTENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"用户说：{user_text}"},
    ]
    result = await ernie_client.chat_with_retry(
        messages, temperature=0.1, max_tokens=200, response_format="json_object",
    )
    try:
        return json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        logger.warning("意图识别返回非 JSON: %s", result["content"][:200])
        return {"intent": "freeChat", "params": {}, "confidence": 0.3}


# ── 调用点 2：任务规划 ────────────────────────────

PLAN_SYSTEM_PROMPT = """你是学习机器人"小伴"的教学规划器。
根据用户意图、用户画像和待复习卡片，生成教学计划。

返回严格 JSON，不要输出其他内容：
{
  "steps": [
    {"type": "warmup|practice|review|report", "topic": "...", "target_grammar": "...", "method": "..."}
  ],
  "estimated_duration": "5min"
}"""


async def plan_teaching(intent: dict, user_id: str) -> dict:
    """调用点 2：任务规划（temperature=0.3，结构化推理）"""
    profile = await get_user_profile(user_id)
    facts = await get_recent_facts(user_id, days=7)
    due_cards = await get_due_cards(user_id)

    context = f"""用户意图：{json.dumps(intent, ensure_ascii=False)}

用户画像：
- 职业：{profile.get('occupation', '未知')}
- 英语水平：{profile.get('english_level', 'B1')}
- 学习目标：{profile.get('learning_goal', '日常英语')}

近期生活事件：
{chr(10).join(f'- {f}' for f in facts) if facts else '- 暂无记录'}

FSRS 到期卡片（需要复习的知识点）：
{chr(10).join(f'- {c["key"]}（难度 {c["difficulty"]:.1f}）' for c in due_cards) if due_cards else '- 暂无到期卡片'}"""

    messages = [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]
    result = await ernie_client.chat_with_retry(
        messages, temperature=0.3, max_tokens=500, response_format="json_object",
    )
    try:
        return json.loads(result["content"])
    except (json.JSONDecodeError, KeyError):
        logger.warning("任务规划返回非 JSON: %s", result["content"][:200])
        return {"steps": [{"type": "warmup", "topic": "自由对话", "method": "聊天"}]}


# ── 调用点 3：对话执行 ────────────────────────────

DIALOGUE_SYSTEM_PROMPT = """你是"小伴"，一个陪伴式英语学习机器人。

## 你对这个用户的了解
{profile_section}

## 今天的教学计划
{plan_section}

## 教学原则
1. 隐式引导：在你的回复中自然使用用户需要强化的表达，让用户在对话中无感接收正确用法
2. 不要直接纠错，而是用自然回复示范正确用法
3. 保持对话自然流畅，像朋友聊天
4. 回复控制在 2-3 句话，简洁自然
5. 用英文回复（除非用户明确用中文提问）"""


async def generate_dialogue(
    plan: dict,
    user_id: str,
    user_text: str,
    history: list[dict],
) -> str:
    """调用点 3：对话生成（temperature=0.7，自然对话）"""
    profile = await get_user_profile(user_id)
    facts = await get_recent_facts(user_id, days=7)

    profile_section = f"""- 职业：{profile.get('occupation', '未知')}
- 英语水平：{profile.get('english_level', 'B1')}
- 学习目标：{profile.get('learning_goal', '日常英语')}
- 近况：{'; '.join(facts[:3]) if facts else '暂无'}"""

    plan_section = json.dumps(plan.get("steps", []), ensure_ascii=False, indent=2)

    system_prompt = DIALOGUE_SYSTEM_PROMPT.format(
        profile_section=profile_section,
        plan_section=plan_section,
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-10:])  # 保留最近 10 轮上下文
    messages.append({"role": "user", "content": user_text})

    result = await ernie_client.chat_with_retry(
        messages, temperature=0.7, max_tokens=300,
    )
    return result["content"]


# ── Agent 主编排 ────────────────────────────────

async def agent_respond(user_text: str, user_id: str, history: list[dict]) -> dict:
    """
    Agent 主流程：意图 → 规划 → 执行

    Returns:
        {
            "reply": "机器人回复",
            "intent": {...},
            "plan": {...},
            "debug": {...},  # Agent 链路调试信息
        }
    """
    # 调用点 1：意图理解
    intent = await classify_intent(user_text)
    logger.info("意图识别: %s (confidence=%.2f)", intent.get("intent"), intent.get("confidence", 0))

    # 低置信度回退自由聊天
    if intent.get("confidence", 0) < 0.5:
        intent = {"intent": "freeChat", "params": {}, "confidence": 0.5}

    # 调用点 2：任务规划
    plan = await plan_teaching(intent, user_id)
    logger.info("教学计划: %d 步", len(plan.get("steps", [])))

    # 调用点 3：对话生成
    reply = await generate_dialogue(plan, user_id, user_text, history)

    return {
        "reply": reply,
        "intent": intent,
        "plan": plan,
        "debug": {
            "intent_result": intent,
            "plan_steps": len(plan.get("steps", [])),
        },
    }
