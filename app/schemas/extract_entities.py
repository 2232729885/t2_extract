"""
`POST /extract_entities` 请求/响应 schema。
对应课题四后端仓库 docs/T2抽取接口规约.md + docs/T2抽取实体与关系说明.md
+ docs/关系词表与头尾实体类型说明.md（16个关系类型，唯一权威来源）。
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.common import CamelModel

# 实体类型只有这4种，不包含 narrative
ENTITY_TYPES = ("person", "organization", "event", "location")

# 16个关系类型，见 docs/关系词表与头尾实体类型说明.md
ALLOWED_PREDICATES = frozenset(
    {
        "HAS_ACCOUNT",
        "BELONGS_TO",
        "PART_OF",
        "PUBLISHED_BY",
        "REPLY_TO",
        "REPOSTS",
        "MENTIONS",
        "DESCRIBES",
        "EVENT_OCCURRED_AT",
        "EVENT_INVOLVES_ENTITY",
        "LOCATED_IN",
        "SUPPORTS",
        "OPPOSES",
        "QUESTIONS",
        "INCITES",
        "DE_ESCALATES",
    }
)

# 人物认知领域类别（8个），见 docs/T2抽取实体与关系说明.md 第1.3节
PERSON_CATEGORIES = (
    "foreign_public_official",
    "key_influencer",
    "domain_expert",
    "media_person",
    "business_figure",
    "civic_actor",
    "active_netizen",
    "general_person",
)

# 组织认知领域类别（5个），见 docs/T2抽取实体与关系说明.md 第1.4节
ORGANIZATION_CATEGORIES = (
    "state_institution",
    "political_organization",
    "social_organization",
    "media_organization",
    "enterprise",
)


# ==================== 请求 ====================


class Context(CamelModel):
    content_id: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    author_handle: Optional[str] = None
    hashtags: list[str] = []
    mentions: list[str] = []
    parent_content_id: Optional[str] = None
    repost_of_content_id: Optional[str] = None
    quoted_content_id: Optional[str] = None


class ExtractRequest(CamelModel):
    title: Optional[str] = None
    text: str
    # T1 entitiesHint 本来就是数组（一条内容可能对应多个实体线索），不是单个对象，
    # 这个字段只是参考用、直接拼进提示词文本，不需要对内部结构做强校验，用 Any 兼容
    # list/dict 等各种实际可能传过来的形状，不要定死成 dict
    annotation: Optional[Any] = None
    context: Optional[Context] = None
    language: Optional[str] = None


# ==================== 响应 ====================


class Span(CamelModel):
    start: int
    end: int


class ExtractedEntity(CamelModel):
    mention_id: str
    name: str
    canonical_name: str
    type: str  # person | organization | event | location
    span: Optional[Span] = None
    aliases: list[str] = []
    importance_score: Optional[float] = None
    confidence: Optional[float] = None
    # person: {"personCategories": [...]}；organization: {"organizationCategories": [...]}；
    # event: {"eventType": ..., "eventTimeStart": ...}；location: {}
    attributes: dict = {}


class ExtractedRelation(CamelModel):
    relation_mention_id: str
    subject_mention_id: str
    predicate: str  # 必须在 ALLOWED_PREDICATES 内
    object_mention_id: str
    confidence: Optional[float] = None
    evidence: Optional[str] = None


class ExtractResponse(CamelModel):
    content_id: Optional[str] = None
    entities: list[ExtractedEntity] = []
    relations: list[ExtractedRelation] = []
    resolved_author_account_id: Optional[str] = None
    model_version: str = "t2-extract-v1.0"
