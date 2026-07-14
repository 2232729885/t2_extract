"""
所有 schema 的公共基类。JSON 走 camelCase（跟后端 Java DTO 的 Jackson 序列化习惯保持一致），
Python 代码内部走 snake_case，通过 alias 互相转换，两边都能用。
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )
