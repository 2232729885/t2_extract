# T2 Extract Entities Service
# 构建：docker build -t t2-extract:latest .
# 运行：docker run -d -p 8002:8002 --env-file .env --name t2-extract t2-extract:latest
#   （.env 参照 .env.example 填好 LLM_BASE_URL 等内网vLLM连接信息）

FROM hlyn3voy1ie4dwn74t.xuanyuan.run/python:3.12-slim

WORKDIR /app

# 系统依赖：几乎不需要额外的系统包，openai/fastapi都是纯Python依赖，curl只是给健康检查用
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# 非root用户运行，降低容器逃逸风险
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# 生产环境不用 --reload，worker数量按实际负载调整
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
