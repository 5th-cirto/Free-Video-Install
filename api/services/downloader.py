from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yt_dlp


class DownloaderError(Exception):
    """Normalized downloader error for API responses."""


class DownloadService:
    def __init__(self, downloads_dir: Path, timeout_seconds: int) -> None:
        self._downloads_dir = downloads_dir
        self._timeout_seconds = timeout_seconds
        self._downloads_dir.mkdir(parents=True, exist_ok=True)
        self._ffmpeg_location = self._detect_ffmpeg_location()

    def inspect(self, url: str) -> dict[str, Any]:
        url = self._normalize_video_url(url)
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": self._timeout_seconds,
        }
        ydl_opts.update(self._site_overrides(url))
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                raw_info = ydl.extract_info(url, download=False)
                info = ydl.sanitize_info(raw_info)
        except Exception as exc:  # noqa: BLE001
            raise DownloaderError(self._normalize_error(exc)) from exc
        return self._normalize_info(info)

    def download(
        self,
        *,
        url: str,
        format_id: Optional[str],
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict[str, Any]:
        url = self._normalize_video_url(url)
        format_selector = self._build_format_selector(url, format_id)
        outtmpl = str(self._downloads_dir / "%(id)s_%(title).80s.%(ext)s")

        def _hook(event: dict[str, Any]) -> None:
            if progress_callback is None:
                return
            status = event.get("status")
            if status == "downloading":
                total = event.get("total_bytes") or event.get("total_bytes_estimate") or 0
                downloaded = event.get("downloaded_bytes") or 0
                progress = (downloaded / total * 100.0) if total else 0.0
                progress_callback(progress)
            elif status == "finished":
                progress_callback(100.0)

        ydl_opts = {
            "format": format_selector,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "windowsfilenames": True,
            "restrictfilenames": True,
            "overwrites": True,
            "continuedl": False,
            "paths": {"home": str(self._downloads_dir)},
            "socket_timeout": self._timeout_seconds,
            "retries": 3,
            "fragment_retries": 3,
            "progress_hooks": [_hook],
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        }
        if self._ffmpeg_location:
            ydl_opts["ffmpeg_location"] = self._ffmpeg_location
        ydl_opts.update(self._site_overrides(url))

        # Bilibili is sensitive to missing referer/user-agent in some regions.
        if "bilibili.com" in url:
            ydl_opts["http_headers"]["Referer"] = "https://www.bilibili.com/"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                info = ydl.sanitize_info(info)
        except Exception as exc:  # noqa: BLE001
            raise DownloaderError(self._normalize_error(exc)) from exc

        requested = info.get("requested_downloads") or []
        filepath = ""
        if requested:
            filepath = requested[0].get("filepath", "")
        if not filepath and info.get("_filename"):
            filepath = info["_filename"]

        actual_path = self._resolve_existing_output_path(filepath, info.get("id"))
        if not actual_path:
            raise DownloaderError("Download finished but output file was not found on disk.")

        return {
            "title": info.get("title"),
            "id": info.get("id"),
            "extractor": info.get("extractor_key") or info.get("extractor"),
            "filepath": str(actual_path),
            "format_selector": format_selector,
        }

    @staticmethod
    def _normalize_error(exc: Exception) -> str:
        text = str(exc).lower()
        if "unsupported url" in text:
            return "Unsupported URL. Please try another link."
        if "not a valid url" in text:
            return "Invalid URL format."
        if "private video" in text or "login required" in text:
            return "This video requires login or access permission."
        if "unable to download webpage" in text:
            return "Unable to access webpage. Check network or geo restrictions."
        if "sign in to confirm" in text:
            return "The platform requests sign-in verification."
        return f"Download failed: {exc}"

    @staticmethod
    def _normalize_info(info: dict[str, Any]) -> dict[str, Any]:
        formats = []
        has_video_only = False
        has_audio_only = False
        has_muxed = False
        for fmt in info.get("formats", []):
            if not fmt.get("format_id"):
                continue
            vcodec = fmt.get("vcodec")
            acodec = fmt.get("acodec")
            if vcodec == "none" and acodec == "none":
                # Skip storyboard/non-media formats from UI options.
                continue
            if vcodec != "none" and acodec == "none":
                has_video_only = True
            elif vcodec == "none" and acodec != "none":
                has_audio_only = True
            elif vcodec != "none" and acodec != "none":
                has_muxed = True
            formats.append(
                {
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "resolution": fmt.get("resolution") or f"{fmt.get('width')}x{fmt.get('height')}",
                    "fps": fmt.get("fps"),
                    "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                    "vcodec": vcodec,
                    "acodec": acodec,
                    "format_note": fmt.get("format_note"),
                }
            )
        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "thumbnail": DownloadService._normalize_thumbnail_url(info.get("thumbnail")),
            "duration": info.get("duration"),
            "extractor": info.get("extractor_key") or info.get("extractor"),
            "formats": formats,
            "is_adaptive_only": bool(has_video_only and has_audio_only and not has_muxed),
        }

    @staticmethod
    def _normalize_thumbnail_url(url: Any) -> Optional[str]:
        if not isinstance(url, str) or not url:
            return None
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("http://"):
            return f"https://{url[7:]}"
        return url

    def _resolve_existing_output_path(self, filepath: str, video_id: Any) -> Optional[Path]:
        if filepath:
            direct = Path(filepath)
            if direct.exists():
                return direct

        # Fallback: yt-dlp may report a pre-sanitized filepath on Windows.
        if isinstance(video_id, str) and video_id:
            marker = f"[{video_id}]"
            candidates = sorted(
                [p for p in self._downloads_dir.iterdir() if p.is_file() and marker in p.name],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return candidates[0]
        return None

    def _build_format_selector(self, url: str, format_id: Optional[str]) -> str:
        if not format_id:
            return "bv*+ba/b"

        # If user selected a video-only format, auto-attach bestaudio to avoid mute output.
        # If user selected an audio-only format, attach bestvideo similarly.
        try:
            probe_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "socket_timeout": self._timeout_seconds,
            }
            probe_opts.update(self._site_overrides(url))
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                info = ydl.sanitize_info(ydl.extract_info(url, download=False))
            fmt = next((f for f in info.get("formats", []) if f.get("format_id") == format_id), None)
            if not fmt:
                return f"{format_id}+bestaudio/b"

            vcodec = (fmt.get("vcodec") or "").lower()
            acodec = (fmt.get("acodec") or "").lower()
            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"

            if has_video and not has_audio:
                return f"{format_id}+bestaudio/b"
            if has_audio and not has_video:
                return f"bestvideo+{format_id}/b"
            return format_id
        except Exception:
            # Safe fallback: prioritize adding audio to avoid mute videos.
            return f"{format_id}+bestaudio/b"

    @staticmethod
    def _detect_ffmpeg_location() -> Optional[str]:
        local_ffmpeg = Path("./tools/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe").resolve()
        if local_ffmpeg.exists():
            return str(local_ffmpeg.parent)

        try:
            import imageio_ffmpeg  # type: ignore

            ffmpeg_bin = Path(imageio_ffmpeg.get_ffmpeg_exe())
            if ffmpeg_bin.exists():
                return str(ffmpeg_bin.parent)
        except Exception:
            return None
        return None

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
    def _normalize_video_url(url: str) -> str:
        value = (url or "").strip()
        if not value:
            return value
        if "bilibili.com/video/" not in value:
            return value
        split = urlsplit(value)
        query_pairs = parse_qsl(split.query, keep_blank_values=False)
        keep_keys = {"p", "t"}
        cleaned_query = urlencode([(k, v) for k, v in query_pairs if k in keep_keys])
        return urlunsplit((split.scheme, split.netloc, split.path, cleaned_query, ""))

