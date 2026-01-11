"""任务队列 - Linux版本（线程队列，无需外部组件）"""
import threading
import queue
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime
try:
    from labprinter_linux import config
except ImportError:
    import config


class TaskState(Enum):
    PENDING = "PENDING"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


@dataclass
class Task:
    id: str
    filepath: str
    options: dict
    original_filename: str = ""
    state: TaskState = TaskState.PENDING
    message: str = "等待处理..."
    progress: int = 0
    result: Any = None
    error: str = None
    created_at: datetime = field(default_factory=datetime.now)


class TaskQueue:
    def __init__(self):
        max_queue_size = getattr(config, "MAX_QUEUE_SIZE", 0) or 0
        try:
            max_queue_size = int(max_queue_size)
        except (TypeError, ValueError):
            max_queue_size = 0
        if max_queue_size < 0:
            max_queue_size = 0
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._tasks: dict[str, Task] = {}
        self._tasks_lock = threading.Lock()

    def submit(self, filepath: str, options: dict, original_filename: str = "") -> str:
        task_id = uuid.uuid4().hex
        task = Task(id=task_id, filepath=filepath, options=options, original_filename=original_filename)

        with self._tasks_lock:
            self._tasks[task_id] = task

        try:
            self._queue.put_nowait(task_id)
        except queue.Full:
            with self._tasks_lock:
                self._tasks.pop(task_id, None)
            raise RuntimeError("任务队列已满，请稍后再试")
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs):
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

    def get_next(self, timeout: float = 1.0) -> Optional[str]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        now = datetime.now()
        with self._tasks_lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if (now - task.created_at).total_seconds() > max_age_seconds
                and task.state in (TaskState.SUCCESS, TaskState.FAILURE)
            ]
            for tid in to_remove:
                del self._tasks[tid]


task_queue = TaskQueue()

_worker_lock = threading.Lock()
_workers_started = False
_cleanup_started = False


def start_worker():
    global _workers_started, _cleanup_started
    with _worker_lock:
        if _workers_started:
            return
        from .print_worker import PrintWorker
        for i in range(config.MAX_CONCURRENT_JOBS):
            worker = PrintWorker(task_queue, name=f"PrintWorker-{i}")
            worker.daemon = True
            worker.start()
        _workers_started = True

        if not _cleanup_started:
            thread = threading.Thread(target=_cleanup_loop, name="TaskCleanup", daemon=True)
            thread.start()
            _cleanup_started = True


def _cleanup_loop():
    retention = getattr(config, "TASK_RETENTION_SECONDS", 3600) or 3600
    interval = getattr(config, "TASK_CLEANUP_INTERVAL_SECONDS", 300) or 300
    try:
        retention = int(retention)
    except (TypeError, ValueError):
        retention = 3600
    try:
        interval = int(interval)
    except (TypeError, ValueError):
        interval = 300
    if retention < 60:
        retention = 60
    if interval < 5:
        interval = 5

    while True:
        try:
            task_queue.cleanup_old_tasks(max_age_seconds=retention)
        except Exception:
            pass
        time.sleep(interval)
