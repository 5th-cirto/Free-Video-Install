from __future__ import annotations

import asyncio
import json
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
                },
            )

            yield _sse_event("stage", {"stage": "summarizing", "message": "DeepSeek is generating summary."})
            service = DeepSeekSummaryService()
            full_text = ""
            async for piece in service.stream_structured_summary(subtitle_result.text):
                full_text += piece
                yield _sse_event("delta", {"text": piece})

            parsed = service.parse_summary_json(full_text)
            yield _sse_event(
                "result",
                {
                    "summary": parsed.summary,
                    "outline": parsed.outline,
                    "key_points": parsed.key_points,
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

