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
