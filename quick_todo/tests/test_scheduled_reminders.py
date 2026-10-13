import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from todo.service import TaskService
from todo.storage import SQLiteTaskRepository


class ScheduledReminderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'tasks.sqlite3'
        self.repo = SQLiteTaskRepository(self.path)
        self.service = TaskService(self.repo)
        self.now = datetime(2026, 10, 13, 16, 0)
        self.at = self.now.replace(hour=17, minute=30)

    def tearDown(self):
        self.repo.close()
        self.temp.cleanup()

    def reopen(self):
        self.repo.close()
        self.repo = SQLiteTaskRepository(self.path)
        self.service = TaskService(self.repo)

    def test_one_time_fires_at_time_once_and_survives_restart(self):
        reminder = self.service.save_reminder('关闭节点', self.at, now=self.now)
        self.reopen()
        self.assertIsNone(self.service.take_due_reminder(self.at - timedelta(seconds=1)))
        self.assertEqual(self.service.take_due_reminder(self.at), reminder)
        self.reopen()
        self.assertIsNone(self.service.take_due_reminder(self.at + timedelta(days=1)))
        self.assertFalse(self.service.reminders()[0].enabled)

    def test_daily_rolls_to_same_local_time_tomorrow(self):
        self.service.save_reminder('每天关闭节点', self.at, daily=True, now=self.now)
        self.service.take_due_reminder(self.at)
        tomorrow = self.at + timedelta(days=1)
        self.assertEqual(self.service.reminders()[0].next_at, tomorrow)
        self.assertIsNone(self.service.take_due_reminder(self.at + timedelta(seconds=1)))
        self.assertIsNotNone(self.service.take_due_reminder(tomorrow))

    def test_daily_created_after_time_starts_tomorrow(self):
        reminder = self.service.save_reminder('关闭节点', self.at, daily=True,
                                               now=self.at + timedelta(minutes=1))
        self.assertEqual(reminder.next_at, self.at + timedelta(days=1))

    def test_daily_missed_days_catch_up_once(self):
        self.service.save_reminder('关闭节点', self.at, daily=True, now=self.now)
        self.reopen()
        resumed = self.at + timedelta(days=5, hours=1)
        self.assertIsNotNone(self.service.take_due_reminder(resumed))
        self.assertIsNone(self.service.take_due_reminder(resumed))
        self.assertEqual(self.service.reminders()[0].next_at, self.at + timedelta(days=6))

    def test_invalid_title_and_past_one_time_do_not_write(self):
        for title, at in [('', self.at), ('x' * 201, self.at), ('过去', self.now)]:
            with self.assertRaises(ValueError):
                self.service.save_reminder(title, at, now=self.now)
        self.assertEqual(self.service.reminders(), [])

    def test_edit_delete_and_regular_tasks_are_independent(self):
        task = self.service.add('普通待办')
        reminder = self.service.save_reminder('关闭节点', self.at, now=self.now)
        changed = self.service.save_reminder('新的事件', self.at + timedelta(hours=1),
                                             reminder=reminder, now=self.now)
        self.assertEqual(changed.id, reminder.id)
        self.assertIsNone(self.service.take_due_reminder(self.at))
        self.service.delete_reminder(changed)
        self.assertEqual(self.service.reminders(), [])
        self.assertEqual(self.service.all(), [task])

    def test_simultaneous_events_are_each_consumed_once(self):
        for title in ('事件一', '事件二', '事件三'):
            self.service.save_reminder(title, self.at, now=self.now)
        titles = {self.service.take_due_reminder(self.at).title for _ in range(3)}
        self.assertEqual(titles, {'事件一', '事件二', '事件三'})
        self.assertIsNone(self.service.take_due_reminder(self.at))

    def test_failed_trigger_save_leaves_reminder_pending(self):
        reminder = self.service.save_reminder('不能漏掉', self.at, now=self.now)
        self.repo.connection.execute('PRAGMA query_only = ON')
        with self.assertRaises(Exception):
            self.service.take_due_reminder(self.at)
        self.assertEqual(self.service.reminders(), [reminder])

    def test_existing_database_gets_reminder_table_without_changing_tasks(self):
        task = self.service.add('原有数据', '不要丢失')
        self.repo.connection.execute('DROP TABLE scheduled_reminders')
        self.repo.connection.commit()
        self.reopen()
        self.assertEqual(self.service.all(), [task])
        self.assertEqual(self.service.reminders(), [])
        self.service.save_reminder('新功能', self.at, now=self.now)
        self.assertEqual(len(self.service.reminders()), 1)


if __name__ == '__main__':
    unittest.main()
