"""应用业务：验证、筛选、排序与状态变更。"""
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from .domain import Task, TaskRepository, ScheduledReminder


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    @staticmethod
    def validate(title: str, notes: str) -> str:
        title = title.strip()
        if not title:
            raise ValueError('请先写下要做的事情。')
        if len(title) > 200:
            raise ValueError('标题最多 200 个字，请把详细内容放进备注。')
        if len(notes) > 10000:
            raise ValueError('备注最多 10000 个字。')
        return title

    def add(self, title: str, notes: str = '', due: Optional[date] = None,
            important: bool = False) -> Task:
        task = Task(uuid4().hex, self.validate(title, notes), notes.strip(), due,
                    important, False, datetime.now())
        self.repository.save(task)
        return task

    def edit(self, task: Task, title: str, notes: str, due: Optional[date],
             important: bool) -> Task:
        updated = replace(task, title=self.validate(title, notes),
                          notes=notes.strip(), due=due, important=important)
        self.repository.save(updated)
        return updated

    def complete(self, task: Task, completed: bool) -> None:
        self.repository.save(replace(task, completed=completed))

    def star(self, task: Task, important: bool) -> None:
        self.repository.save(replace(task, important=important))

    def delete(self, task: Task) -> None:
        self.repository.delete(task.id)

    def restore(self, task: Task) -> None:
        self.repository.save(task)

    def all(self) -> List[Task]:
        return self.repository.all()

    def reminders(self) -> List[ScheduledReminder]:
        return sorted(self.repository.all_reminders(), key=lambda r: (not r.enabled, r.next_at, r.id))

    def save_reminder(self, title: str, at: datetime, daily: bool = False,
                      reminder: Optional[ScheduledReminder] = None,
                      now: Optional[datetime] = None) -> ScheduledReminder:
        now = now or datetime.now()
        title = self.validate(title, '')
        at = at.replace(second=0, microsecond=0)
        if daily:
            at = datetime.combine(now.date(), at.time())
            if at <= now:
                at += timedelta(days=1)
        elif at <= now:
            raise ValueError('提醒时间已经过去，请选择未来的日期和时间。')
        saved = ScheduledReminder(reminder.id if reminder else uuid4().hex, title, at, daily)
        self.repository.save_reminder(saved)
        return saved

    def delete_reminder(self, reminder: ScheduledReminder) -> None:
        self.repository.delete_reminder(reminder.id)

    def take_due_reminder(self, now: Optional[datetime] = None) -> Optional[ScheduledReminder]:
        """每次取最早的一条，成功保存触发状态后再交给界面显示。"""
        now = now or datetime.now()
        due = next((r for r in self.reminders() if r.enabled and r.next_at <= now), None)
        if due is None:
            return None
        if due.daily:
            next_at = datetime.combine(now.date(), due.next_at.time())
            if next_at <= now:
                next_at += timedelta(days=1)
            updated = replace(due, next_at=next_at)
        else:
            updated = replace(due, enabled=False)
        self.repository.save_reminder(updated)
        return due

    @staticmethod
    def select(tasks: List[Task], view: str = 'inbox', query: str = '',
               today: Optional[date] = None) -> List[Task]:
        today = today or date.today()
        query = query.strip().casefold()
        def matches(task: Task) -> bool:
            if view == 'completed':
                visible = task.completed
            elif view == 'today':
                visible = not task.completed and task.due is not None and task.due <= today
            elif view == 'important':
                visible = not task.completed and task.important
            else:
                visible = not task.completed
            return visible and query in (task.title + '\n' + task.notes).casefold()
        return sorted((t for t in tasks if matches(t)), key=lambda t: (
            not t.important, t.due or date.max, -t.created_at.timestamp(), t.id))
