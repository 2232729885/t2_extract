"""
基础冒烟测试：只验证 schema 能不能正确解析请求/响应样例，不依赖真实大模型调用。
"""
import json

from app.schemas.extract_entities import ALLOWED_PREDICATES, ExtractRequest, ExtractResponse


def test_extract_request_parses_real_sample():
    sample = {
        "title": None,
        "text": "keep red and we can narrow it down to that one part of the south china sea",
        "annotation": None,
        "context": {
            "contentId": "osqm1if",
            "platform": "reddit",
            "url": "https://reddit.com/xyz",
            "publishedAt": "2026-06-20T10:05:59.627Z",
            "authorHandle": "Mysterious_Hope_1586",
            "hashtags": [],
            "mentions": [],
            "parentContentId": None,
            "repostOfContentId": None,
            "quotedContentId": None,
        },
        "language": "en",
    }
    request = ExtractRequest.model_validate(sample)
    assert request.context.content_id == "osqm1if"
    assert request.text.startswith("keep red")


def test_extract_response_round_trips_camel_case_and_span_object():
    sample = {
        "contentId": "abc123",
        "entities": [
            {
                "mentionId": "m1",
                "name": "CENTCOM",
                "canonicalName": "U.S. Central Command",
                "type": "organization",
                "span": {"start": 0, "end": 7},
                "aliases": ["U.S. Central Command"],
                "importanceScore": 90.0,
                "confidence": 0.97,
                "attributes": {"organizationCategories": ["state_institution"]},
            },
            {
                "mentionId": "p1",
                "name": "John Smith",
                "canonicalName": "John Smith",
                "type": "person",
                "span": {"start": 20, "end": 30},
                "aliases": [],
                "attributes": {"personCategories": ["media_person", "key_influencer"]},
            },
        ],
        "relations": [
            {
                "relationMentionId": "r1",
                "subjectMentionId": "p1",
                "predicate": "BELONGS_TO",
                "objectMentionId": "m1",
                "confidence": 0.85,
            }
        ],
        "resolvedAuthorAccountId": None,
        "modelVersion": "t2-extract-v1.0",
    }
    response = ExtractResponse.model_validate(sample)
    assert response.entities[0].span.start == 0
    assert response.entities[1].attributes["personCategories"] == ["media_person", "key_influencer"]
    dumped = json.loads(response.model_dump_json(by_alias=True))
    assert dumped["entities"][0]["canonicalName"] == "U.S. Central Command"
    assert dumped["relations"][0]["subjectMentionId"] == "p1"


def test_allowed_predicates_has_exactly_16():
    assert len(ALLOWED_PREDICATES) == 16
    assert "SUPPORTS" in ALLOWED_PREDICATES
    assert "AFFILIATED_WITH" not in ALLOWED_PREDICATES  # 已废弃的旧关系名，不应该在词表内


def test_annotation_field_accepts_list_not_just_dict():
    """
    2026-07-14生产环境真实422错误：T1的entitiesHint本来就是数组（一条内容可能对应多个
    实体线索），之前把annotation字段类型定死成dict，后端真实传过来的是list时直接校验失败。
    """
    request = ExtractRequest.model_validate(
        {
            "text": "CATL is a battery manufacturer",
            "annotation": [
                {
                    "text": "CATL",
                    "typeHint": "organizations",
                    "evidenceIds": ["ev_001"],
                    "entityHintId": "ent_001",
                    "entityHintConfidence": 0.95,
                },
                {
                    "text": "CYATY",
                    "typeHint": "organizations",
                    "evidenceIds": ["ev_001"],
                    "entityHintId": "ent_002",
                    "entityHintConfidence": 0.9,
                },
            ],
            "context": {"contentId": "abc123"},
            "language": "en",
        }
    )
    assert isinstance(request.annotation, list)
    assert len(request.annotation) == 2


def test_null_list_fields_are_treated_as_empty():
    """
    Java DTO 的 List<X> 字段没有值时，Jackson 序列化出来是显式的 null，不是省略key也不是[]。
    context.hashtags/mentions 显式传 null 时应该被当成空列表处理，不能校验失败
    （这是2026-07-14生产环境真实报过的一个422错误，t1_annotation项目同样的问题，这里同步补测试）。
    """
    request = ExtractRequest.model_validate(
        {
            "title": None,
            "text": "some text",
            "annotation": None,
            "context": {
                "contentId": "abc123",
                "platform": "reddit",
                "hashtags": None,
                "mentions": None,
            },
            "language": "en",
        }
    )
    assert request.context.hashtags == []
    assert request.context.mentions == []


def test_llm_client_limits_concurrent_requests(monkeypatch):
    """
    T1/T2共用同一个vLLM实例，2026-07-14生产环境真实事故（并发请求太多把vLLM的GPU显存
    压爆导致引擎崩溃）同样会影响T2，这里同步补上跟t1_annotation项目一样的并发限制验证。
    """
    import threading
    import time
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("LLM_MAX_CONCURRENT_REQUESTS", "2")
    from app.llm_client import LlmClient

    with patch("app.llm_client.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]

        concurrent_count = [0]
        max_concurrent = [0]
        lock = threading.Lock()

        def slow_create(*args, **kwargs):
            with lock:
                concurrent_count[0] += 1
                max_concurrent[0] = max(max_concurrent[0], concurrent_count[0])
            time.sleep(0.1)
            with lock:
                concurrent_count[0] -= 1
            return mock_response

        mock_client.chat.completions.create.side_effect = slow_create

        client = LlmClient()
        threads = [threading.Thread(target=client.call_json, args=("sys", "user")) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert max_concurrent[0] <= 2
