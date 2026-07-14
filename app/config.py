"""
配置项。所有配置通过环境变量注入，不在代码里硬编码任何密钥。
本地开发时复制 .env.example 为 .env 并填入真实值。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 通义千问 DashScope OpenAI 兼容模式
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen-max"

    # LLM调用参数
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    # 服务本身
    service_port: int = 8002
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
