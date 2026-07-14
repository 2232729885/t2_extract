"""
T2 实体关系抽取服务 - FastAPI 入口。

  POST /extract_entities   实体关系抽取（mention级，不做实体消歧）

对应 docs/T2抽取接口规约.md（课题四后端仓库）。
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas.extract_entities import ExtractRequest, ExtractResponse
from app.services import extract_service

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="T2 Extract Entities Service",
    description="实体关系抽取（mention级），课题四 T2 算法接口实现",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    FastAPI 默认422只把detail塞进响应体返回给调用方，自己的容器日志里不会打印具体原因。
    这里补一份服务端自己的日志，以后422发生时直接在这个服务的容器日志里就能看到详细原因。
    """
    body = await request.body()
    logger.error(
        "422 Unprocessable Entity on %s %s\nvalidation errors: %s\nraw request body: %s",
        request.method, request.url.path, exc.errors(), body.decode("utf-8", errors="replace")[:5000],
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract_entities", response_model=ExtractResponse)
def extract_entities(request: ExtractRequest) -> ExtractResponse:
    return extract_service.extract_entities(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.service_port, reload=True)
