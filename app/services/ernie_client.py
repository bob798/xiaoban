"""
文心大模型 API 客户端（千帆 v2 协议）

v2 接口采用 OpenAI 兼容格式 + IAM 安全认证（Bearer token），
不再使用旧版 access_token 刷新流程。
"""

import time
import asyncio
import httpx
from app.config import settings
from app.logger import get_logger

logger = get_logger("ernie_client")

# 千帆 v2 API（OpenAI 兼容）
BASE_URL = "https://qianfan.baidubce.com/v2"

# 模型降级链
ERNIE_MODELS = [
    "ernie-4.0-turbo-8k",
    "ernie-3.5-turbo-128k",
]


def _get_headers() -> dict:
    """IAM 认证 Header"""
    return {
        "Authorization": f"Bearer {settings.BAIDU_API_KEY}",
        "Content-Type": "application/json",
    }


async def chat(
    messages: list[dict],
    model: str = "ernie-4.0-turbo-8k",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: str | None = None,
) -> dict:
    """
    调用文心大模型 v2 API（OpenAI 兼容格式）

    Args:
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
                  v2 协议原生支持 system role，无需手动合并
        model: 模型标识
        temperature: 0.0-1.0
        max_tokens: 最大输出 token 数
        response_format: 设为 "json_object" 强制 JSON 输出

    Returns:
        {"content": "模型回复", "usage": {"total_tokens": N}}
    """
    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format == "json_object":
        body["response_format"] = {"type": "json_object"}

    url = f"{BASE_URL}/chat/completions"
    t0 = time.time()

    async with httpx.AsyncClient(trust_env=False, timeout=30.0) as client:
        resp = await client.post(url, headers=_get_headers(), json=body)
        resp.raise_for_status()
        data = resp.json()

    elapsed = time.time() - t0

    # v2 错误格式
    if "error" in data:
        err = data["error"]
        logger.error("文心 API 错误: type=%s msg=%s 耗时=%.2fs",
                      err.get("type"), err.get("message"), elapsed)
        raise RuntimeError(f"文心 API 错误: {err.get('message')}")

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    logger.info("文心 chat 完成 model=%s 耗时=%.2fs tokens=%s",
                model, elapsed, usage.get("total_tokens"))
    return {"content": content, "usage": usage}


async def chat_with_retry(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: str | None = None,
) -> dict:
    """
    带重试和模型降级的文心 API 调用

    策略：ERNIE-4.0 超时 → 重试 1 次 → 降级到 ERNIE-3.5
    """
    for model in ERNIE_MODELS:
        for attempt in range(2):
            try:
                result = await asyncio.wait_for(
                    chat(messages, model=model, temperature=temperature,
                         max_tokens=max_tokens, response_format=response_format),
                    timeout=15.0,
                )
                if model != ERNIE_MODELS[0]:
                    logger.warning("已降级到 %s", model)
                return result
            except (asyncio.TimeoutError, httpx.HTTPError, RuntimeError) as e:
                logger.warning("%s 第 %d 次调用失败: %s", model, attempt + 1, e)
                if attempt == 0:
                    await asyncio.sleep(1)
                continue
        continue

    return {"content": "抱歉，AI 服务暂时不可用。", "usage": {}}
