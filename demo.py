"""
小伴 Demo — 直接运行查看 Agent 链路结果

用法：python demo.py
"""

import asyncio
import time
from app.database import create_tables
from app.services.agent_service import agent_respond

SCENARIOS = [
    "开始今天的英语练习",
    "帮我复习上次的错误",
    "总结我这周的学习情况",
]


async def main():
    await create_tables()
    print("=" * 60)
    print("  小伴 — 基于文心大模型的陪伴式学习机器人")
    print("  Agent 链路演示（3 组指令）")
    print("=" * 60)

    for i, text in enumerate(SCENARIOS, 1):
        print(f"\n{'─' * 60}")
        print(f"  指令 {i}：{text}")
        print(f"{'─' * 60}")

        t0 = time.time()
        result = await agent_respond(text, "demo-user", [])
        elapsed = time.time() - t0

        intent = result["intent"]
        plan = result["plan"]

        print(f"\n  [调用点1 意图识别]  intent={intent.get('intent')}  confidence={intent.get('confidence')}")

        steps = plan.get("steps", [])
        print(f"  [调用点2 任务规划]  {len(steps)} 步")
        for j, s in enumerate(steps, 1):
            print(f"    step{j}: {s.get('type')} — {s.get('topic', '')}")

        print(f"  [调用点3 对话生成]")
        print(f"\n  小伴: {result['reply']}")
        print(f"\n  耗时: {elapsed:.1f}s")

    print(f"\n{'=' * 60}")
    print("  3 组指令全部完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
