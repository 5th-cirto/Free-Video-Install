from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
from pathlib import Path
import os
import subprocess
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from api.config import settings
from api.schemas import BatchDownloadRequest, DownloadRequest, InspectRequest, SubtitleDownloadRequest
from api.services.subtitle_extractor import SubtitleExtractor, SubtitleExtractorError
from api.services.downloader import DownloadService, DownloaderError
from api.services.tasks import TaskManager

router = APIRouter(prefix="/api/video", tags=["video"])

task_manager = TaskManager(max_parallel_downloads=settings.max_parallel_downloads)
download_service = DownloadService(
    downloads_dir=settings.downloads_dir,
    timeout_seconds=settings.request_timeout_seconds,
)
subtitle_extractor = SubtitleExtractor(timeout_seconds=settings.request_timeout_seconds)
executor = ThreadPoolExecutor(max_workers=max(settings.max_parallel_downloads, 2))


def _run_download(task_id: str, url: str, format_id: Optional[str]) -> None:
    task_manager.acquire_slot()
    task_manager.update(task_id, status="running", progress=1.0)
    try:
        progress = lambda value: _progress_hook(task_id, value)
        result = download_service.download(url=url, format_id=format_id, progress_callback=progress)
        task_manager.update(task_id, status="success", progress=100.0, result=result)
    except Exception as exc:  # noqa: BLE001 - normalize all downloader errors
        task_manager.update(task_id, status="failed", error=str(exc))
    finally:
        task_manager.release_slot()


def _progress_hook(task_id: str, progress: float) -> None:
    task_manager.update(task_id, progress=progress)


def _format_subtitle_time(seconds: float, *, srt_style: bool) -> str:
    total_ms = max(0, int(round((seconds or 0.0) * 1000)))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    millis = total_ms % 1000
    separator = "," if srt_style else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def _segments_to_srt(segments: list[dict[str, Any]]) -> str:
    rows = []
    for idx, seg in enumerate(segments, start=1):
        start = _format_subtitle_time(float(seg.get("start") or 0.0), srt_style=True)
        end = _format_subtitle_time(float(seg.get("end") or 0.0), srt_style=True)
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        rows.append(f"{idx}\n{start} --> {end}\n{text}")
    return "\n\n".join(rows).strip()


def _segments_to_vtt(segments: list[dict[str, Any]]) -> str:
    rows = ["WEBVTT", ""]
    for seg in segments:
        start = _format_subtitle_time(float(seg.get("start") or 0.0), srt_style=False)
        end = _format_subtitle_time(float(seg.get("end") or 0.0), srt_style=False)
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        rows.append(f"{start} --> {end}")
        rows.append(text)
        rows.append("")
    return "\n".join(rows).strip()


def _build_subtitle_content(format_name: str, subtitle_text: str, segments: list[dict[str, Any]]) -> tuple[str, str]:
    if format_name == "txt":
        return subtitle_text.strip(), "text/plain; charset=utf-8"
    if format_name == "vtt":
        return _segments_to_vtt(segments), "text/vtt; charset=utf-8"
    return _segments_to_srt(segments), "application/x-subrip; charset=utf-8"


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^\w\-.]+", "_", value.strip(), flags=re.UNICODE)
    return cleaned[:80] or "subtitle"


@router.post("/inspect")
def inspect_video(payload: InspectRequest) -> dict[str, Any]:
    try:
        return {"success": True, "message": "ok", "data": download_service.inspect(payload.url)}
    except DownloaderError as exc:
        raise HTTPException(status_code=400, detail=f"Inspect failed: {exc}") from exc


@router.post("/download")
def create_download(payload: DownloadRequest) -> dict[str, Any]:
    task = task_manager.create_task("single", {"url": payload.url, "format_id": payload.format_id})
    executor.submit(_run_download, task["task_id"], payload.url, payload.format_id)
    return {"success": True, "message": "task created", "data": task}


@router.post("/download/batch")
def create_batch_download(payload: BatchDownloadRequest) -> dict[str, Any]:
    tasks = []
    for url in payload.urls:
        task = task_manager.create_task("batch-item", {"url": url, "format_id": payload.format_id})
        tasks.append(task)
        executor.submit(_run_download, task["task_id"], url, payload.format_id)
    return {"success": True, "message": "batch tasks created", "data": {"tasks": tasks}}


@router.post("/subtitles/download")
def download_subtitles(payload: SubtitleDownloadRequest) -> Response:
    try:
        result = subtitle_extractor.extract_text(payload.url.strip(), payload.language)
        content, media_type = _build_subtitle_content(payload.format, result.text, result.segments)
    except SubtitleExtractorError as exc:
        raise HTTPException(status_code=400, detail=f"Subtitle extraction failed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Subtitle export failed: {exc}") from exc

    if not content.strip():
        raise HTTPException(status_code=400, detail="Subtitle content is empty.")

    filename = _safe_filename(f"subtitle_{result.language}.{payload.format}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content.encode("utf-8"), media_type=media_type, headers=headers)


@router.get("/tasks")
def list_tasks() -> dict[str, Any]:
    return {"success": True, "message": "ok", "data": {"tasks": task_manager.list()}}


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "message": "ok", "data": task}


@router.get("/config")
def get_runtime_config() -> dict[str, Any]:
    return {
        "success": True,
        "message": "ok",
        "data": {
            "downloads_dir": str(settings.downloads_dir),
        },
    }


@router.post("/open-path")
def open_path(path: str) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")
    try:
        if os.name == "nt":
            # Open folder and select file when possible
            if target.is_file():
                subprocess.Popen(["explorer", "/select,", str(target)])
            else:
                os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
            subprocess.Popen([opener, str(target.parent if target.is_file() else target)])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Open path failed: {exc}") from exc
    return {"success": True, "message": "ok", "data": {"path": str(target)}}


@router.get("/thumbnail")
def proxy_thumbnail(url: str) -> Response:
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid thumbnail URL")
    candidate_urls = [url]
    if url.startswith("https://"):
        candidate_urls.append(f"http://{url[8:]}")
    try:
        with httpx.Client(timeout=20, follow_redirects=True, verify=False) as client:
            last_error: Optional[Exception] = None
            for current_url in candidate_urls:
                try:
                    resp = client.get(
                        current_url,
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0.0.0 Safari/537.36"
                            ),
                            "Referer": "https://www.bilibili.com/",
                        },
                    )
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "image/jpeg")
                    return Response(content=resp.content, media_type=content_type)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
            raise last_error or RuntimeError("Thumbnail request failed")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Thumbnail fetch failed: {exc}") from exc

