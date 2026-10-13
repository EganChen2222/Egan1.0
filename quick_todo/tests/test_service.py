import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from todo.service import TaskService
from todo.storage import SQLiteTaskRepository


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'tasks.sqlite3'
        self.repo = SQLiteTaskRepository(self.path)
        self.service = TaskService(self.repo)

    def tearDown(self):
        self.repo.close()
        self.temp.cleanup()

    def test_validation_does_not_write(self):
        for title, notes in [('  ', ''), ('a' * 201, ''), ('ok', 'a' * 10001)]:
            with self.assertRaises(ValueError):
                self.service.add(title, notes)
        self.assertEqual(self.service.all(), [])

    def test_edit_completion_and_persistence(self):
        original = self.service.add('  中文任务  ', '备注')
        edited = self.service.edit(original, '修改标题', '详细备注', date(2026, 10, 15), True)
        self.service.complete(edited, True)
        self.repo.close()
        self.repo = SQLiteTaskRepository(self.path)
        self.service = TaskService(self.repo)
        saved, = self.service.all()
        self.assertEqual(saved.title, '修改标题')
        self.assertEqual(saved.due, date(2026, 10, 15))
        self.assertTrue(saved.completed and saved.important)
        self.assertEqual(saved.created_at, original.created_at)
        self.service.complete(saved, False)
        self.assertFalse(self.service.all()[0].completed)

    def test_views_include_overdue_and_exclude_completed(self):
        today = date(2026, 10, 13)
        overdue = self.service.add('逾期', due=today - timedelta(days=1))
        due = self.service.add('今天', due=today)
        self.service.add('明天', due=today + timedelta(days=1))
        self.service.add('随手记')
        done = self.service.add('已完成', due=today)
        self.service.complete(done, True)
        selected = self.service.select(self.service.all(), 'today', today=today)
        self.assertEqual([t.id for t in selected], [overdue.id, due.id])
        self.assertEqual(len(self.service.select(self.service.all(), 'inbox')), 4)
        self.assertEqual(len(self.service.select(self.service.all(), 'completed')), 1)

    def test_search_notes_and_star_sort(self):
        self.service.add('普通', notes='Searchable NOTES')
        important = self.service.add('重要', important=True)
        self.assertEqual(self.service.select(self.service.all())[0].id, important.id)
        self.assertEqual(len(self.service.select(self.service.all(), query=' notes ')), 1)
        self.service.star(important, False)
        self.assertEqual(self.service.select(self.service.all(), 'important'), [])

    def test_delete_and_restore_all_fields(self):
        task = self.service.add('恢复我', '备注', date.today(), True)
        self.service.delete(task)
        self.assertEqual(self.service.all(), [])
        self.service.restore(task)
        self.assertEqual(self.service.all(), [task])

    def test_failed_write_leaves_existing_data(self):
        original = self.service.add('不能丢失')
        self.repo.connection.execute('PRAGMA query_only = ON')
        with self.assertRaises(Exception):
            self.service.edit(original, '失败修改', '', None, False)
        self.assertEqual(self.service.all(), [original])


if __name__ == '__main__':
    unittest.main()
