"""
POST /extract_entities 的业务逻辑：拼用户提示词 -> 调大模型 -> 解析成 ExtractResponse
-> 过滤掉不在16个词表内的 predicate。
"""
import logging

from pydantic import ValidationError

from app.llm_client import LlmCallError, get_llm_client
from app.prompts import EXTRACT_ENTITIES_SYSTEM_PROMPT
from app.schemas.extract_entities import ALLOWED_PREDICATES, ExtractRequest, ExtractResponse

logger = logging.getLogger(__name__)


def _build_user_prompt(request: ExtractRequest) -> str:
    parts: list[str] = []
    if request.title:
        parts.append(f"Title: {request.title}")
    parts.append(f"Text: {request.text}")

    if request.annotation:
        parts.append(f"T1 annotation hints (for reference only, not authoritative): {request.annotation}")

    ctx = request.context
    if ctx is not None:
        if ctx.platform:
            parts.append(f"Platform: {ctx.platform}")
        if ctx.hashtags:
            parts.append(f"Hashtags: {', '.join(ctx.hashtags)}")
        if ctx.mentions:
            parts.append(f"Mentions: {', '.join(ctx.mentions)}")

    return "\n\n".join(parts)


def _filter_invalid_predicates(response: ExtractResponse) -> ExtractResponse:
    """predicate 不在16个词表内的关系直接丢弃，不寄希望于大模型100%守规矩。"""
    kept = [r for r in response.relations if r.predicate in ALLOWED_PREDICATES]
    dropped = len(response.relations) - len(kept)
    if dropped:
        logger.warning("Dropped %s relation(s) with predicate outside the 16-type vocabulary", dropped)
    response.relations = kept
    return response


def _build_fallback_response(request: ExtractRequest) -> ExtractResponse:
    response = ExtractResponse()
    response.content_id = request.context.content_id if request.context else None
    response.entities = []
    response.relations = []
    response.resolved_author_account_id = None
    return response


def extract_entities(request: ExtractRequest) -> ExtractResponse:
    try:
        raw = get_llm_client().call_json(EXTRACT_ENTITIES_SYSTEM_PROMPT, _build_user_prompt(request))
        response = ExtractResponse.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        logger.error("extract_entities failed, falling back to empty result: %s", exc)
        return _build_fallback_response(request)

    response = _filter_invalid_predicates(response)
    response.content_id = request.context.content_id if request.context else response.content_id
    return response
