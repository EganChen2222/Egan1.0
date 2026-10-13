"""纯 Python 领域模型与持久化接口，不依赖 Qt 或 SQLite。"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    notes: str
    due: Optional[date]
    important: bool
    completed: bool
    created_at: datetime


class TaskRepository(Protocol):
    def all(self) -> List[Task]: ...
    def save(self, task: Task) -> None: ...
    def delete(self, task_id: str) -> None: ...
