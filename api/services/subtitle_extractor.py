from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Any, Optional

import httpx
import yt_dlp


@dataclass
class SubtitleExtractResult:
    language: str
    source: str
    text: str
    segments: list[dict[str, Any]]


class SubtitleExtractorError(Exception):
    """Raised when subtitle extraction fails."""


class SubtitleExtractor:
    def __init__(self, timeout_seconds: int = 60) -> None:
        self._timeout_seconds = timeout_seconds

    def extract_text(self, url: str, preferred_language: Optional[str] = None) -> SubtitleExtractResult:
        url = self._normalize_video_url(url)
        info = self._extract_info(url)
        subtitles = info.get("subtitles") or {}
        automatic_captions = info.get("automatic_captions") or {}

        preferred_langs = self._build_language_priority(preferred_language)
        picked = self._pick_track(subtitles, preferred_langs)
        source = "manual_subtitle"
        if not picked:
            picked = self._pick_track(automatic_captions, preferred_langs)
            source = "automatic_caption"
        if not picked and "bilibili.com" in url:
            # Fallback for Bilibili: subtitles may be missing in yt-dlp info
            # while still available via player wbi API.
            fallback = self._extract_bilibili_subtitle_via_api(url, preferred_langs)
            if fallback:
                return fallback
        if not picked:
            raise SubtitleExtractorError("Current video has no available platform subtitles.")

        lang, track = picked
        subtitle_text, subtitle_segments = self._download_and_parse_track(
            url=url,
            language=lang,
            preferred_ext=track.get("ext"),
            source=source,
        )
        if not subtitle_text.strip():
            raise SubtitleExtractorError("Subtitle extraction succeeded but no readable text was found.")

        return SubtitleExtractResult(
            language=lang,
            source=source,
            text=subtitle_text,
            segments=subtitle_segments,
        )

    @staticmethod
    def _normalize_video_url(url: str) -> str:
        value = (url or "").strip()
        if not value:
            return value
        if "bilibili.com/video/" in value and "www.bilibili.com/video/" not in value:
            return value.replace("://bilibili.com/video/", "://www.bilibili.com/video/")
        return value

    def _extract_bilibili_subtitle_via_api(
        self, url: str, preferred_langs: list[str]
    ) -> Optional[SubtitleExtractResult]:
        bvid = self._extract_bvid(url)
        if not bvid:
            return None
        headers = self._bilibili_headers()
        cookie_header = self._cookie_header_from_cookiefile()
        if cookie_header:
            headers["Cookie"] = cookie_header

        try:
            with httpx.Client(timeout=self._timeout_seconds, verify=False, trust_env=False) as client:
                view_resp = client.get(
                    "https://api.bilibili.com/x/web-interface/view",
                    params={"bvid": bvid},
                    headers=headers,
                )
                view_resp.raise_for_status()
                view_data = (view_resp.json() or {}).get("data") or {}
                aid = view_data.get("aid")
                pages = view_data.get("pages") or []
                cid = (pages[0] or {}).get("cid") if pages else None
                if not aid or not cid:
                    return None

                player_resp = client.get(
                    "https://api.bilibili.com/x/player/wbi/v2",
                    params={"aid": aid, "cid": cid},
                    headers=headers,
                )
                player_resp.raise_for_status()
                player_data = (player_resp.json() or {}).get("data") or {}
                subtitle_items = ((player_data.get("subtitle") or {}).get("subtitles") or [])
                if not subtitle_items:
                    return None

                selected = self._pick_bilibili_subtitle_item(subtitle_items, preferred_langs)
                if not selected:
                    return None

                subtitle_url = selected.get("subtitle_url") or ""
                if subtitle_url.startswith("//"):
                    subtitle_url = f"https:{subtitle_url}"
                if not subtitle_url:
                    return None

                sub_resp = client.get(subtitle_url, headers=headers)
                sub_resp.raise_for_status()
                body = sub_resp.json() if "application/json" in (sub_resp.headers.get("content-type") or "") else {}
                entries = body.get("body") or []
                text_lines = []
                segments: list[dict[str, Any]] = []
                for item in entries:
                    content = str((item or {}).get("content") or "").strip()
                    if content:
                        text_lines.append(content)
                        segments.append(
                            {
                                "start": float((item or {}).get("from") or 0.0),
                                "end": float((item or {}).get("to") or 0.0),
                                "text": content,
                            }
                        )
                text = "\n".join(text_lines).strip()
                if not text:
                    return None
                return SubtitleExtractResult(
                    language=str(selected.get("lan") or "unknown"),
                    source="bilibili_player_api",
                    text=text,
                    segments=segments,
                )
        except Exception:
            return None

    @staticmethod
    def _extract_bvid(url: str) -> Optional[str]:
        match = re.search(r"/video/(BV[0-9A-Za-z]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _bilibili_headers() -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.bilibili.com/",
        }

    @staticmethod
    def _pick_bilibili_subtitle_item(
        items: list[dict[str, Any]], preferred_langs: list[str]
    ) -> Optional[dict[str, Any]]:
        # prefer exact language first
        for lang in preferred_langs:
            for item in items:
                if str(item.get("lan") or "").lower() == lang.lower() and item.get("subtitle_url"):
                    return item
        # then prefer Chinese-like entries
        for item in items:
            lan = str(item.get("lan") or "").lower()
            if ("zh" in lan or "ai-zh" == lan) and item.get("subtitle_url"):
                return item
        # fallback first item with subtitle_url
        return next((it for it in items if it.get("subtitle_url")), None)

    @staticmethod
    def _cookie_header_from_cookiefile() -> str:
        cookiefile = os.getenv("YTDLP_COOKIEFILE", "").strip()
        if not cookiefile:
            return ""
        path = Path(cookiefile)
        if not path.exists():
            return ""
        pairs: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                text = line.strip()
                if not text or text.startswith("#"):
                    continue
                parts = text.split("\t")
                if len(parts) >= 7 and "bilibili.com" in parts[0]:
                    pairs.append(f"{parts[5]}={parts[6]}")
        except Exception:
            return ""
        return "; ".join(pairs)

    def _extract_info(self, url: str) -> dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": self._timeout_seconds,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        }
        ydl_opts.update(self._site_overrides(url))
        cookiefile = os.getenv("YTDLP_COOKIEFILE", "").strip()
        cookies_from_browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip()
        if cookiefile:
            ydl_opts["cookiefile"] = cookiefile
        if cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
        if "bilibili.com" in url:
            ydl_opts["http_headers"]["Referer"] = "https://www.bilibili.com/"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                raw = ydl.extract_info(url, download=False)
                return ydl.sanitize_info(raw)
        except Exception as exc:  # noqa: BLE001
            text = str(exc).lower()
            if "bilibili" in url and "403" in text:
                raise SubtitleExtractorError(
                    "Bilibili blocked metadata access (403). Please provide a logged-in cookie/cookiefile for Bilibili, then retry."
                ) from exc
            raise SubtitleExtractorError(f"Failed to inspect subtitles: {exc}") from exc

    @staticmethod
    def _site_overrides(url: str) -> dict[str, Any]:
        if "youtube.com" in url or "youtu.be" in url:
            return {
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android_vr"],
                    }
                }
            }
        return {}

    @staticmethod
    def _build_language_priority(preferred_language: Optional[str]) -> list[str]:
        priority = []
        if preferred_language:
            priority.append(preferred_language)
        priority.extend(["zh-CN", "zh-Hans", "zh", "en", "en-US"])
        seen: set[str] = set()
        result = []
        for item in priority:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _pick_track(track_map: dict[str, Any], language_priority: list[str]) -> Optional[tuple[str, dict[str, Any]]]:
        for lang in language_priority:
            if lang in track_map:
                picked = SubtitleExtractor._pick_best_format(track_map.get(lang) or [])
                if picked:
                    return lang, picked

        for lang, items in track_map.items():
            picked = SubtitleExtractor._pick_best_format(items or [])
            if picked:
                return lang, picked
        return None

    @staticmethod
    def _pick_best_format(items: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not items:
            return None
        ext_priority = ["vtt", "srv3", "srv2", "srv1", "ttml", "json3"]
        for ext in ext_priority:
            for item in items:
                if item.get("ext") == ext and item.get("url"):
                    return item
        return next((item for item in items if item.get("url")), None)

    def _download_and_parse_track(
        self,
        *,
        url: str,
        language: str,
        preferred_ext: Any,
        source: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        # Let yt-dlp download subtitle files directly to avoid SSL/cert differences
        # between subtitle hosts and this runtime.
        prefer_auto = source == "automatic_caption"
        pref_ext = (preferred_ext or "vtt")
        with TemporaryDirectory(prefix="subtitle_") as tmpdir:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "socket_timeout": self._timeout_seconds,
                "writesubtitles": not prefer_auto,
                "writeautomaticsub": prefer_auto,
                "subtitleslangs": [language],
                "subtitlesformat": f"{pref_ext}/vtt/best",
                "outtmpl": str(Path(tmpdir) / "%(id)s.%(ext)s"),
                "http_headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            }
            ydl_opts.update(self._site_overrides(url))
            cookiefile = os.getenv("YTDLP_COOKIEFILE", "").strip()
            cookies_from_browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip()
            if cookiefile:
                ydl_opts["cookiefile"] = cookiefile
            if cookies_from_browser:
                ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
            if "bilibili.com" in url:
                ydl_opts["http_headers"]["Referer"] = "https://www.bilibili.com/"
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as exc:  # noqa: BLE001
                raise SubtitleExtractorError(f"Failed to download subtitle track: {exc}") from exc

            subtitle_file = self._find_subtitle_file(Path(tmpdir), language)
            if not subtitle_file:
                raise SubtitleExtractorError("Subtitle file was not generated by extractor.")
            raw_text = subtitle_file.read_text(encoding="utf-8", errors="ignore")
            suffix = subtitle_file.suffix.lower()
            if suffix in {".vtt", ".srv3", ".srv2", ".srv1"}:
                segments = self._parse_vtt_like_segments(raw_text)
                return self._segments_to_text(segments), segments
            if suffix == ".json3":
                segments = self._parse_json3_segments(raw_text)
                return self._segments_to_text(segments), segments
            if suffix == ".ttml":
                text = self._normalize_caption_text(raw_text)
                return text, [{"start": 0.0, "end": 0.0, "text": line} for line in text.splitlines() if line]
            text = raw_text.strip()
            return text, [{"start": 0.0, "end": 0.0, "text": line} for line in text.splitlines() if line]

    @staticmethod
    def _find_subtitle_file(tmp_path: Path, language: str) -> Optional[Path]:
        files = sorted([p for p in tmp_path.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return None
        lang_token = f".{language}."
        for file in files:
            if lang_token in file.name:
                return file
        return files[0]

    @staticmethod
    def _normalize_caption_text(raw_text: str) -> str:
        lines = []
        for line in raw_text.splitlines():
            text = line.strip()
            if not text:
                continue
            if text.startswith("WEBVTT"):
                continue
            if "-->" in text:
                continue
            if text.isdigit():
                continue
            if text.startswith("<") and text.endswith(">"):
                continue
            cleaned = (
                text.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&nbsp;", " ")
            )
            lines.append(cleaned)
        return "\n".join(lines)

    @staticmethod
    def _parse_vtt_like_segments(raw_text: str) -> list[dict[str, Any]]:
        segments: list[dict[str, Any]] = []
        lines = raw_text.splitlines()
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if "-->" not in line:
                idx += 1
                continue
            start_str, end_str = [part.strip() for part in line.split("-->", 1)]
            start = SubtitleExtractor._parse_timestamp(start_str)
            end = SubtitleExtractor._parse_timestamp(end_str.split(" ")[0])
            idx += 1
            texts: list[str] = []
            while idx < len(lines):
                text = lines[idx].strip()
                if not text:
                    break
                if "-->" in text:
                    break
                texts.append(text)
                idx += 1
            content = " ".join(texts).strip()
            if content:
                segments.append({"start": start, "end": end, "text": content})
            idx += 1
        return segments

    @staticmethod
    def _parse_json3_segments(raw_text: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(raw_text)
        except Exception:
            return []
        events = data.get("events") or []
        segments: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            segs = event.get("segs") or []
            if not segs:
                continue
            text = "".join(str(seg.get("utf8") or "") for seg in segs).strip()
            if not text:
                continue
            start = float(event.get("tStartMs") or 0) / 1000.0
            duration = float(event.get("dDurationMs") or 0) / 1000.0
            end = start + duration
            segments.append({"start": start, "end": end, "text": text})
        return segments

    @staticmethod
    def _parse_timestamp(value: str) -> float:
        text = value.replace(",", ".").strip()
        parts = text.split(":")
        try:
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            return float(text)
        except Exception:
            return 0.0

    @staticmethod
    def _segments_to_text(segments: list[dict[str, Any]]) -> str:
        return "\n".join(str(item.get("text") or "").strip() for item in segments if str(item.get("text") or "").strip())

