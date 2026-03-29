from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.config import settings
from api.services.ai_summary import AISummaryError, DeepSeekSummaryService
from api.services.subtitle_extractor import SubtitleExtractor, SubtitleExtractorError

router = APIRouter(prefix="/api/ai-summary", tags=["ai-summary"])

subtitle_extractor = SubtitleExtractor(timeout_seconds=settings.request_timeout_seconds)


class SummaryStreamRequest(BaseModel):
    url: str = Field(..., min_length=3, description="Video URL")
    language: Optional[str] = Field(default=None, description="Preferred subtitle language, e.g. zh-CN/en")


def _sse_event(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


def _extract_json_candidate(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0:
        return ""
    if end <= start:
        return text[start:]
    return text[start : end + 1]


def _extract_partial_string(candidate: str, key: str) -> str:
    # Best effort extraction from partial JSON strings.
    pattern = rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"])*)'
    match = re.search(pattern, candidate, flags=re.DOTALL)
    if not match:
        return ""
    value = match.group(1)
    return value.replace('\\"', '"').replace("\\n", "\n").strip()


def _extract_partial_array(candidate: str, key: str) -> list[str]:
    pattern = rf'"{re.escape(key)}"\s*:\s*\[(.*?)(?:\]|$)'
    match = re.search(pattern, candidate, flags=re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    items = re.findall(r'"((?:\\.|[^"])*)"', body)
    cleaned = []
    for item in items:
        value = item.replace('\\"', '"').replace("\\n", "\n").strip()
        if value:
            cleaned.append(value)
    return cleaned


def _extract_partial_result(raw_text: str) -> dict[str, Any]:
    candidate = _extract_json_candidate(raw_text)
    if not candidate:
        return {}
    try:
        data = json.loads(candidate)
        return {
            "summary": str(data.get("summary") or "").strip(),
            "outline": [str(i).strip() for i in (data.get("outline") or []) if str(i).strip()],
            "key_points": [str(i).strip() for i in (data.get("key_points") or []) if str(i).strip()],
            "mindmap_mermaid": str(data.get("mindmap_mermaid") or "").strip(),
        }
    except Exception:
        return {
            "summary": _extract_partial_string(candidate, "summary"),
            "outline": _extract_partial_array(candidate, "outline"),
            "key_points": _extract_partial_array(candidate, "key_points"),
            "mindmap_mermaid": _extract_partial_string(candidate, "mindmap_mermaid"),
        }


@router.post("/stream")
async def stream_summary(payload: SummaryStreamRequest) -> StreamingResponse:
    async def event_generator():
        try:
            yield _sse_event("stage", {"stage": "started", "message": "Summary request accepted."})
            subtitle_result = await asyncio.to_thread(
                subtitle_extractor.extract_text,
                payload.url.strip(),
                payload.language,
            )
            yield _sse_event(
                "stage",
                {
                    "stage": "subtitle_ready",
                    "language": subtitle_result.language,
                    "source": subtitle_result.source,
                    "chars": len(subtitle_result.text),
                    "segments": len(subtitle_result.segments),
                },
            )

            yield _sse_event("stage", {"stage": "summarizing", "message": "DeepSeek is generating summary."})
            service = DeepSeekSummaryService()
            full_text = ""
            last_partial_signature = ""
            async for piece in service.stream_structured_summary(subtitle_result.text):
                full_text += piece
                yield _sse_event("delta", {"text": piece})
                partial = _extract_partial_result(full_text)
                if partial:
                    signature = json.dumps(partial, ensure_ascii=False, sort_keys=True)
                    if signature != last_partial_signature:
                        last_partial_signature = signature
                        yield _sse_event("partial_result", partial)

            parsed = service.parse_summary_json(full_text)
            yield _sse_event(
                "result",
                {
                    "summary": parsed.summary,
                    "outline": parsed.outline,
                    "key_points": parsed.key_points,
                    "mindmap_mermaid": parsed.mindmap_mermaid,
                    "subtitle_text": subtitle_result.text,
                    "subtitle_segments": subtitle_result.segments,
                    "language": subtitle_result.language,
                    "subtitle_source": subtitle_result.source,
                },
            )
            yield _sse_event("done", {"ok": True})
        except (SubtitleExtractorError, AISummaryError) as exc:
            yield _sse_event("error", {"message": str(exc)})
            yield _sse_event("done", {"ok": False})
        except Exception as exc:  # noqa: BLE001
            yield _sse_event("error", {"message": f"Unexpected error: {exc}"})
            yield _sse_event("done", {"ok": False})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

