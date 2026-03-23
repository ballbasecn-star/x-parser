"""统一 parser 契约适配。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from flask import jsonify

from xparser.models import ParseResult, TweetInfo
from xparser.url_detector import URLDetector

PARSER_VERSION = "0.1.0"
_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


class UnsupportedUrlError(ValueError):
    """输入链接不属于当前 parser。"""


def create_request_id() -> str:
    return f"req_{uuid4().hex}"


def contract_success_response(request_id: str, data: Any, status_code: int = 200):
    return (
        jsonify(
            {
                "success": True,
                "data": data,
                "error": None,
                "meta": {
                    "requestId": request_id,
                    "parserVersion": PARSER_VERSION,
                },
            }
        ),
        status_code,
    )


def contract_error_response(request_id: str, code: str, message: str, status_code: int, retryable: bool):
    return (
        jsonify(
            {
                "success": False,
                "data": None,
                "error": {
                    "code": code,
                    "message": message,
                    "retryable": retryable,
                },
                "meta": {
                    "requestId": request_id,
                    "parserVersion": PARSER_VERSION,
                },
            }
        ),
        status_code,
    )


def build_health_payload() -> dict[str, str]:
    return {"status": "UP"}


def build_capabilities_payload() -> dict[str, Any]:
    return {
        "platform": "x",
        "supportedSourceTypes": ["thread", "share_text"],
        "features": {
            "transcript": False,
            "images": True,
            "metrics": True,
            "authorProfile": True,
            "deepAnalysis": False,
            "batchParse": True,
            "asyncParse": False,
        },
    }


def resolve_source_url(payload: Optional[dict]) -> str:
    if not payload:
        raise ValueError("请提供 JSON 数据")

    input_payload = payload.get("input") or {}
    source_text = (input_payload.get("sourceText") or "").strip()
    source_url = (input_payload.get("sourceUrl") or "").strip()
    resolved_source = source_url or extract_url_from_text(source_text)

    if not resolved_source:
        raise ValueError("sourceText 和 sourceUrl 不能同时为空")

    detection = URLDetector().detect(resolved_source)
    if not detection.is_valid or not detection.tweet_id:
        raise UnsupportedUrlError(detection.error or "当前 parser 仅支持 X/Twitter 推文链接")
    return detection.url


def extract_language_hint(payload: Optional[dict]) -> Optional[str]:
    return ((payload or {}).get("options") or {}).get("languageHint") or None


def to_parsed_content_payload(result: ParseResult, language_hint: Optional[str]) -> dict[str, Any]:
    tweet = result.tweet or TweetInfo()
    warnings = []
    if not tweet.images and not tweet.videos:
        warnings.append(
            {
                "code": "MEDIA_UNAVAILABLE",
                "message": "当前返回未包含图片或视频资源。",
            }
        )

    return {
        "platform": "x",
        "sourceType": "thread",
        "externalId": tweet.tweet_id or None,
        "canonicalUrl": tweet.url,
        "title": tweet.title or derive_title(tweet),
        "summary": tweet.content_clean or None,
        "author": {
            "externalAuthorId": tweet.username or None,
            "name": tweet.display_name or None,
            "handle": tweet.username or None,
            "profileUrl": tweet.author_url or None,
            "avatarUrl": tweet.author_avatar,
        },
        "publishedAt": normalize_datetime(tweet),
        "language": language_hint or tweet.lang or None,
        "content": {
            "rawText": tweet.content_clean or tweet.content or None,
            "transcript": None,
            "segments": [],
        },
        "metrics": {
            "views": tweet.metrics.views or 0,
            "likes": tweet.metrics.likes or 0,
            "comments": tweet.metrics.replies or 0,
            "shares": tweet.metrics.retweets or 0,
            "favorites": tweet.metrics.bookmarks or 0,
        },
        "tags": tweet.hashtags,
        "media": {
            "covers": compact_media([media_item(tweet.images[0], None) if tweet.images else None]),
            "images": compact_media([media_item(url, None) for url in tweet.images]),
            "videos": compact_media([media_item(url, None) for url in tweet.videos]),
            "audios": [],
        },
        "rawPayload": {
            "source": result.source,
            "processingTime": result.processing_time,
            "mentions": tweet.mentions,
            "isQuote": tweet.is_quote,
            "isReply": tweet.is_reply,
            "rawData": tweet.raw_data,
        },
        "warnings": warnings,
    }


def extract_url_from_text(source_text: str) -> str:
    match = _URL_PATTERN.search(source_text)
    return match.group(0) if match else ""


def derive_title(tweet: TweetInfo) -> str:
    content = tweet.content_clean or tweet.content or ""
    content = content.strip()
    return content[:120] if content else (tweet.tweet_id or "X Thread")


def normalize_datetime(tweet: TweetInfo) -> Optional[str]:
    if tweet.created_timestamp:
        try:
            return datetime.fromtimestamp(tweet.created_timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        except (OSError, OverflowError, ValueError):
            return None

    value = (tweet.created_at or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return None


def media_item(url: Optional[str], mime_type: Optional[str]) -> Optional[dict[str, Any]]:
    if not url:
        return None
    return {
        "url": url,
        "mimeType": mime_type,
        "width": None,
        "height": None,
        "durationMs": None,
    }


def compact_media(items: list[Optional[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [item for item in items if item]
