from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx


class AISummaryError(Exception):
    """Raised when AI summary generation fails."""


@dataclass
class SummaryPayload:
    summary: str
    outline: list[str]
    key_points: list[str]


class DeepSeekSummaryService:
    def __init__(self) -> None:
        self._api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self._base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
        self._model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
        self._timeout_seconds = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "120"))
        # System HTTP(S)_PROXY may break TLS in some Windows setups.
        # We disable trust_env by default and allow explicit proxy config.
        self._proxy_url = os.getenv("DEEPSEEK_PROXY_URL", "").strip()
        if not self._api_key:
            raise AISummaryError("DEEPSEEK_API_KEY is not configured.")

    async def stream_structured_summary(self, transcript_text: str) -> AsyncIterator[str]:
        if not transcript_text.strip():
            raise AISummaryError("Transcript text is empty.")

        prompt = self._build_prompt(transcript_text)
        payload = {
            "model": self._model,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是专业的视频学习总结助手。"
                        "你必须只输出合法 JSON，不要输出任何额外解释。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self._base_url}/v1/chat/completions"

        try:
            client_kwargs: dict[str, Any] = {
                "timeout": self._timeout_seconds,
                "verify": False,
                "trust_env": False,
            }
            if self._proxy_url:
                client_kwargs["proxy"] = self._proxy_url
            async with httpx.AsyncClient(**client_kwargs) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = (
                                (((chunk.get("choices") or [{}])[0]).get("delta") or {}).get("content")
                                or ""
                            )
                        except Exception:  # noqa: BLE001
                            delta = ""
                        if delta:
                            yield delta
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise AISummaryError(f"DeepSeek request failed: {detail}") from exc
        except Exception as exc:  # noqa: BLE001
            raise AISummaryError(f"DeepSeek streaming failed: {exc!r}") from exc

    @staticmethod
    def parse_summary_json(raw_text: str) -> SummaryPayload:
        text = raw_text.strip()
        if not text:
            raise AISummaryError("AI returned empty content.")
        try:
            data = json.loads(text)
        except Exception:  # noqa: BLE001
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise AISummaryError("AI output is not valid JSON.")
            try:
                data = json.loads(text[start : end + 1])
            except Exception as exc:  # noqa: BLE001
                raise AISummaryError("AI output JSON parse failed.") from exc

        summary = str(data.get("summary") or "").strip()
        outline = [str(item).strip() for item in (data.get("outline") or []) if str(item).strip()]
        key_points = [str(item).strip() for item in (data.get("key_points") or []) if str(item).strip()]
        if not summary and not outline and not key_points:
            raise AISummaryError("AI output has no valid summary fields.")
        return SummaryPayload(summary=summary, outline=outline, key_points=key_points)

    @staticmethod
    def _build_prompt(transcript_text: str) -> str:
        clipped = transcript_text[:30000]
        return (
            "请根据以下视频字幕，生成学习导向的结构化总结。\n"
            "输出要求：\n"
            "1) 只输出 JSON，不要使用 markdown。\n"
            "2) JSON schema 必须为："
            '{"summary":"string","outline":["string"],"key_points":["string"]}\n'
            "3) summary 用 120-220 字概括视频主旨。\n"
            "4) outline 输出 4-8 条按逻辑顺序的大纲。\n"
            "5) key_points 输出 5-10 条可执行/可记忆知识点。\n\n"
            f"字幕内容：\n{clipped}"
        )

