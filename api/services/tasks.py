from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock, Semaphore
from typing import Any, Dict, List, Optional
from uuid import uuid4


class TaskManager:
    def __init__(self, max_parallel_downloads: int) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self._download_limiter = Semaphore(max_parallel_downloads)

    def create_task(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        task_id = str(uuid4())
        task = {
            "task_id": task_id,
            "kind": kind,
            "status": "queued",
            "progress": 0.0,
            "payload": payload,
            "result": None,
            "error": None,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        with self._lock:
            self._tasks[task_id] = task
        return task.copy()

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.copy() if task else None

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            tasks = [task.copy() for task in self._tasks.values()]
        return sorted(tasks, key=lambda item: item["created_at"], reverse=True)

    def update(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            if task_id not in self._tasks:
                return
            task = self._tasks[task_id]
            if status is not None:
                task["status"] = status
            if progress is not None:
                task["progress"] = max(0.0, min(100.0, progress))
            if result is not None:
                task["result"] = result
            if error is not None:
                task["error"] = error
            task["updated_at"] = self._now()

    def acquire_slot(self) -> None:
        self._download_limiter.acquire()

    def release_slot(self) -> None:
        self._download_limiter.release()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

