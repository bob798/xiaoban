# 小伴（XiaoBan）— 基于文心大模型的陪伴式学习机器人

一个放在书桌上、能看到你、听懂你、记得住你的学习机器人。

## 核心能力

- **Agent 架构**：三阶段文心 API 调用（意图识别 -> 学习规划 -> 对话生成）
- **长期记忆**：用户画像 + 生活事实持久化，跨会话记忆
- **FSRS 科学调度**：间隔重复算法自动安排语法卡片复习时间
- **具身交互**：面向地平线 RDK X3 部署，支持摄像头与语音输入

## 快速启动

### 方式一：Docker

```bash
cp .env.example .env   # 填写 BAIDU_API_KEY
docker compose up
```

服务启动后访问 http://localhost:8000

### 方式二：本地开发

```bash
pip install -r requirements.txt
cp .env.example .env   # 填写 BAIDU_API_KEY
uvicorn main:app --reload
```

### 环境变量

| 变量名 | 说明 |
|--------|------|
| `BAIDU_API_KEY` | 千帆平台 IAM 认证密钥（Bearer token） |
| `DATABASE_URL` | 数据库连接串，默认 `sqlite+aiosqlite:///xiaoban.db` |

## 项目结构

```
xiaoban/
├── main.py                        # FastAPI 入口，路由注册
├── requirements.txt
├── docker-compose.yml
├── app/
│   ├── config.py                  # 环境变量配置
│   ├── database.py                # SQLAlchemy 异步引擎
│   ├── models.py                  # ORM 模型（UserProfile, GrammarCard 等）
│   ├── routers/
│   │   ├── chat.py                # 对话 API
│   │   ├── memory.py              # 记忆管理 API
│   │   └── fsrs.py                # 知识卡片 API
│   └── services/
│       ├── agent_service.py       # Agent 三阶段链路
│       ├── ernie_client.py        # 文心大模型客户端（带降级）
│       ├── memory_service.py      # 用户画像与事实存储
│       └── fsrs_service.py        # FSRS 卡片调度
└── docs/                          # 方案文档
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 对话（同步） |
| POST | `/api/chat/stream` | 对话（SSE 流式） |
| GET  | `/api/memory/profile/{user_id}` | 获取用户画像 |
| PUT  | `/api/memory/profile/{user_id}` | 更新用户画像 |
| GET  | `/api/memory/facts/{user_id}` | 获取近期事实 |
| POST | `/api/memory/facts/{user_id}` | 添加用户事实 |
| GET  | `/api/memory/cards/{user_id}` | 获取全部知识卡片 |
| GET  | `/api/memory/cards/{user_id}/due` | 获取待复习卡片 |
| POST | `/api/cards/{user_id}` | 创建知识卡片 |
| POST | `/api/cards/{user_id}/{card_id}/review` | 复习打分（1-4） |
| GET  | `/health` | 健康检查 |

## 技术栈

- **后端框架**：FastAPI + Uvicorn
- **大模型**：文心大模型 v2（千帆 OpenAI 兼容接口），模型降级链 ernie-4.0-turbo-8k -> ernie-3.5-turbo-128k
- **数据库**：SQLite（aiosqlite 异步驱动）+ SQLAlchemy 2.0
- **记忆调度**：FSRS（py-fsrs >= 4.0）
- **部署**：Docker Compose，目标硬件 RDK X3

## License

MIT
