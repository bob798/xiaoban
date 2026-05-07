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

## Demo 演示

启动服务后打开 http://localhost:8000 ，页面左侧为对话区，右侧为 Agent 调试面板。

依次输入以下 3 组指令，观察右侧面板展示的文心 API 3 次调用链路：

```
开始今天的英语练习          → 意图=practice，机器人发起角色扮演教学
帮我复习上次的错误          → 意图=review，查询 FSRS 到期卡片并引导复习
总结我这周的学习情况        → 意图=summary，聚合学习数据生成进度报告
```

每组指令的处理链路：

```
用户输入
  → 文心 API 调用 1：意图识别（t=0.1）
  → 查询记忆系统（用户画像 + FSRS 卡片）
  → 文心 API 调用 2：任务规划（t=0.3）
  → 文心 API 调用 3：对话生成（t=0.7）
  → 返回回复 + 右侧面板展示完整调试信息
```

也可以通过 API 直接调用：

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "开始今天的英语练习", "user_id": "demo"}'
```

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
