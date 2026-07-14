# T2 Extract Entities Service

课题四 T2 算法接口的 Python 实现，基于 FastAPI，大模型走内网 vLLM 部署的 Qwen3（OpenAI 兼容接口，跟课题四后端连的是同一个模型服务）。

对应规约文档（课题四后端仓库 `docs/` 目录）：
- `T2抽取接口规约.md` —— 接口调用方式（请求/响应字段）
- `T2抽取实体与关系说明.md` —— 该抽取哪些实体类别、哪些关系，判断标准
- `关系词表与头尾实体类型说明.md` —— 16个关系类型唯一权威来源

## 接口

`POST /extract_entities` —— 从文本里抽取 mention 级的实体和关系，不做实体消歧（消歧是T3的活）。

## 快速开始（本地）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env：填入内网 vLLM 的 LLM_BASE_URL（形如 http://<内网地址>:8000/v1）和 LLM_MODEL

uvicorn app.main:app --reload --port 8002
```

启动后访问 `http://localhost:8002/docs` 看自动生成的接口文档。

## 用 Docker 部署

```bash
docker build -t t2-extract:latest .

# .env 参照 .env.example 先建好，填真实的 LLM_BASE_URL 等
docker run -d -p 8002:8002 --env-file .env --name t2-extract t2-extract:latest

# 如果 vLLM 部署在宿主机上（不是内网其他机器），容器内访问宿主机用 host.docker.internal
# （Linux 上可能需要 docker run 加 --add-host=host.docker.internal:host-gateway）
```

看日志 / 健康检查：

```bash
docker logs -f t2-extract
curl http://localhost:8002/health
```

## 目录结构

```
app/
  main.py                    FastAPI入口
  config.py                  环境变量配置
  llm_client.py               大模型调用封装（跟t1_annotation项目共用同一份实现，OpenAI兼容接口）
  prompts.py                  系统提示词（实体类型/认知领域类别/16个关系类型/6个核心关系判断标准）
  schemas/
    common.py                 驼峰命名基类
    extract_entities.py       请求/响应schema，常量：ENTITY_TYPES / ALLOWED_PREDICATES /
                               PERSON_CATEGORIES / ORGANIZATION_CATEGORIES
  services/
    extract_service.py        业务逻辑，包含 predicate 过滤（不在16词表内的关系直接丢弃）
tests/
  test_schemas.py             schema 冒烟测试（不需要真实连上vLLM）
Dockerfile
.dockerignore
```

## 设计说明

- **`predicate` 会做二次过滤**：即使系统提示词已经要求大模型只用16个关系类型，`extract_service.py` 里还是会在拿到大模型结果之后再过滤一遍不在词表内的 `predicate`（`_filter_invalid_predicates`），不完全信任大模型100%守规矩，宁可丢掉一条可疑关系也不要把脏数据传给后端。
- **`attributes.personCategories`/`organizationCategories` 允许为空、允许多标签**，不是必填枚举，具体8类人物/5类组织的定义写在 `app/prompts.py` 里，跟后端仓库的 `T2抽取实体与关系说明.md` 保持同源。
- **不需要输出"内容指向实体"的关系**（`DESCRIBES`/`MENTIONS`那种），后端会自动补，提示词里已经明确告诉大模型不用管这个。
- 大模型调用失败时返回**空的 entities/relations 数组**（`_build_fallback_response`），不是报错，让流水线可以继续往下走，只是这条内容没抽到东西。
- **`llm_client.py` 会自动剥离 `<think>...</think>`**——Qwen3 是推理模型，vLLM 部署时如果没有关掉思考模式，返回内容前面可能带一段思考过程，这段会被自动去掉再解析JSON。
- **`LLM_USE_JSON_RESPONSE_FORMAT`**：vLLM 是否支持 `response_format={"type":"json_object"}` 取决于具体版本和启动参数，不支持的话在 `.env` 里改成 `false`。

## 测试

```bash
pytest
```
