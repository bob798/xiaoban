import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # 千帆 v2 IAM 认证
    BAIDU_API_KEY: str = os.getenv("BAIDU_API_KEY", "")

    # 应用配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///xiaoban.db")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))


settings = Settings()
