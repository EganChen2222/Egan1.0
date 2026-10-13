"""SQLite 适配器：每次写入独立事务，成功后才返回。"""
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List

from .domain import Task


class SQLiteTaskRepository:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), timeout=5)
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    notes TEXT NOT NULL, due TEXT,
                    important INTEGER NOT NULL, completed INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def all(self) -> List[Task]:
        rows = self.connection.execute("SELECT * FROM tasks").fetchall()
        return [Task(
            id=r['id'], title=r['title'], notes=r['notes'],
            due=date.fromisoformat(r['due']) if r['due'] else None,
            important=bool(r['important']), completed=bool(r['completed']),
            created_at=datetime.fromisoformat(r['created_at']),
        ) for r in rows]

    def save(self, task: Task) -> None:
        with self.connection:
            self.connection.execute("""
                INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, notes=excluded.notes, due=excluded.due,
                    important=excluded.important, completed=excluded.completed
            """, (task.id, task.title, task.notes,
                  task.due.isoformat() if task.due else None,
                  int(task.important), int(task.completed), task.created_at.isoformat()))

    def delete(self, task_id: str) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def close(self) -> None:
        self.connection.close()
