import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
import threading
import unittest
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from todo.global_hotkey import CtrlSpaceChord, GlobalQuickCapture, WindowsHookBackend


class ChordTests(unittest.TestCase):
    def test_ctrl_space_once_per_press_and_release_after_ctrl(self):
        chord = CtrlSpaceChord()
        self.assertEqual(chord.process(0x20, True, True), (True, True))
        self.assertEqual(chord.process(0x20, True, True), (True, False))
        self.assertEqual(chord.process(0x20, False, False), (True, False))
        self.assertEqual(chord.process(0x20, True, True), (True, True))

    def test_plain_space_other_keys_and_modified_chords_pass_through(self):
        chord = CtrlSpaceChord()
        for key, down, ctrl, modifier in [(0x20, True, False, False),
                                         (0x20, False, False, False),
                                         (0x44, True, True, False),
                                         (0x20, True, True, True),
                                         (0x20, False, True, True)]:
            self.assertEqual(chord.process(key, down, ctrl, modifier), (False, False))

    def test_native_modifier_mapping_accepts_both_ctrl_keys_only(self):
        for held, expected in [({0xA2}, (True, True)), ({0xA3}, (True, True)),
                               ({0x5B}, (False, False)), ({0x5C}, (False, False)),
                               ({0xA2, 0x10}, (False, False)),
                               ({0xA2, 0x12}, (False, False)),
                               ({0xA2, 0x5B}, (False, False)),
                               ({0xA3, 0x5C}, (False, False)), (set(), (False, False))]:
            with self.subTest(held=held):
                backend = WindowsHookBackend.__new__(WindowsHookBackend)
                backend.user32 = Mock()
                backend.user32.GetAsyncKeyState.side_effect = lambda vk: 0x8000 if vk in held else 0
                backend.chord = CtrlSpaceChord()
                self.assertEqual(backend.process_key(0x20, True), expected)


class HotkeyLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_worker_stops_and_releases_backend(self):
        started = threading.Event()
        released = threading.Event()

        class Backend:
            def run(self, stop_event, activated, ready):
                ready(True, 'ready')
                started.set()
                stop_event.wait(2)
                released.set()

            def stop(self):
                pass

        hotkey = GlobalQuickCapture(backend_factory=Backend)
        with patch('todo.global_hotkey.sys.platform', 'win32'):
            hotkey.start()
            try:
                self.assertTrue(started.wait(2))
                thread = hotkey.thread
                hotkey.start()
                self.assertIs(hotkey.thread, thread)
            finally:
                hotkey.stop()
        self.assertTrue(released.is_set())
        self.assertFalse(hotkey.thread.is_alive())
        hotkey.stop()  # shutdown remains safe when called twice

    def test_backend_error_is_reported(self):
        class BrokenBackend:
            def run(self, *args):
                raise OSError('hook unavailable')

            def stop(self):
                pass

        hotkey = GlobalQuickCapture(backend_factory=BrokenBackend)
        messages = []
        hotkey.status_changed.connect(lambda ok, message: messages.append((ok, message)))
        with patch('todo.global_hotkey.sys.platform', 'win32'):
            with self.assertLogs(level='ERROR'):
                hotkey.start()
                hotkey.thread.join(2)
        self.app.processEvents()
        self.assertFalse(messages[0][0])
        hotkey.stop()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows native hook')
    def test_native_hook_install_and_release_without_sending_keys(self):
        ready = threading.Event()
        errors = []
        stopped = threading.Event()
        backend = WindowsHookBackend()

        def run():
            try:
                backend.run(stopped, lambda: None, lambda ok, message: ready.set())
            except Exception as error:
                errors.append(str(error))
                ready.set()

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        try:
            self.assertTrue(ready.wait(3), 'Hook installation timed out')
            self.assertEqual(errors, [])
            self.assertIsNotNone(backend.thread_id)
        finally:
            stopped.set()
            backend.stop()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertIsNone(backend.thread_id)
