"""
T2 实体关系抽取服务 - FastAPI 入口。

  POST /extract_entities   实体关系抽取（mention级，不做实体消歧）

对应 docs/T2抽取接口规约.md（课题四后端仓库）。
"""
import logging

from fastapi import FastAPI

from app.config import get_settings
from app.schemas.extract_entities import ExtractRequest, ExtractResponse
from app.services import extract_service

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="T2 Extract Entities Service",
    description="实体关系抽取（mention级），课题四 T2 算法接口实现",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract_entities", response_model=ExtractResponse)
def extract_entities(request: ExtractRequest) -> ExtractResponse:
    return extract_service.extract_entities(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.service_port, reload=True)
