"""Windows Ctrl+Space adapter. No task, storage or widget dependencies.

Use WH_KEYBOARD_LL on a dedicated message-loop thread to consume the chord
before an input method can handle it. No text is stored or input synthesized.
Qt signals cross back to the UI thread before any window work is performed.
"""
import ctypes
import logging
import sys
import threading
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal


VK_SPACE = 0x20
VK_LCONTROL, VK_RCONTROL = 0xA2, 0xA3
VK_LWIN, VK_RWIN = 0x5B, 0x5C
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0104, 0x0105
WM_QUIT = 0x0012


class CtrlSpaceChord:
    """Recognize a chord and suppress repeat/keyup without retaining typed keys."""
    def __init__(self):
        self.captured = False

    def process(self, key, down, ctrl_pressed, other_modifier=False):
        if key != VK_SPACE:
            return False, False
        if self.captured:
            if not down:
                self.captured = False
            return True, False
        if down and ctrl_pressed and not other_modifier:
            self.captured = True
            return True, True
        return False, False


class _KeyboardData(ctypes.Structure):
    _fields_ = [('vkCode', wintypes.DWORD), ('scanCode', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]


class WindowsHookBackend:
    def __init__(self):
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                               wintypes.WPARAM, wintypes.LPARAM)
        signatures = {
            'SetWindowsHookExW': ([ctypes.c_int, self.callback_type, wintypes.HINSTANCE, wintypes.DWORD], wintypes.HANDLE),
            'UnhookWindowsHookEx': ([wintypes.HANDLE], wintypes.BOOL),
            'CallNextHookEx': ([wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM], ctypes.c_ssize_t),
            'GetAsyncKeyState': ([ctypes.c_int], ctypes.c_short),
            'PeekMessageW': ([ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
            'GetMessageW': ([ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
            'PostThreadMessageW': ([wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.user32, name)
            function.argtypes, function.restype = arguments, result
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self.kernel32.GetCurrentThreadId.argtypes = []
        self.kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self.thread_id = None
        self.chord = CtrlSpaceChord()
        self.callback = None

    def process_key(self, key, down):
        pressed = lambda vk: bool(self.user32.GetAsyncKeyState(vk) & 0x8000)
        return self.chord.process(
            key, down, pressed(VK_LCONTROL) or pressed(VK_RCONTROL),
            any(pressed(vk) for vk in (0x10, 0x12, VK_LWIN, VK_RWIN)))

    def run(self, stop_event, activated, ready):
        message = wintypes.MSG()
        # Create a thread message queue before publishing its id for stop().
        self.user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        self.thread_id = self.kernel32.GetCurrentThreadId()

        def callback(code, event, pointer):
            if code >= 0 and event in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
                key = ctypes.cast(pointer, ctypes.POINTER(_KeyboardData)).contents
                # Ignore synthesized input from other applications.
                if not key.flags & 0x10 and key.vkCode == VK_SPACE:
                    consume, trigger = self.process_key(
                        key.vkCode, event in (WM_KEYDOWN, WM_SYSKEYDOWN))
                    if trigger:
                        activated()
                    if consume:
                        return 1
            return self.user32.CallNextHookEx(None, code, event, pointer)

        self.callback = self.callback_type(callback)
        handle = self.user32.SetWindowsHookExW(
            13, self.callback, self.kernel32.GetModuleHandleW(None), 0)
        if not handle:
            self.thread_id = None
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            ready(True, 'Ctrl + 空格  桌面速记')
            while not stop_event.is_set():
                result = self.user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == 0:
                    break
        finally:
            self.user32.UnhookWindowsHookEx(handle)
            self.thread_id = None
            self.callback = None

    def stop(self):
        if self.thread_id is not None:
            self.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


class GlobalQuickCapture(QObject):
    activated = Signal()
    status_changed = Signal(bool, str)

    def __init__(self, parent=None, backend_factory=WindowsHookBackend):
        super().__init__(parent)
        self.backend_factory = backend_factory
        self.backend = None
        self.thread = None
        self.stop_event = threading.Event()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        if sys.platform != 'win32':
            self.status_changed.emit(False, '桌面快捷键仅支持 Windows；可使用 Ctrl + N。')
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name='quick-todo-hotkey', daemon=True)
        self.thread.start()

    def _run(self):
        try:
            self.backend = self.backend_factory()
            self.backend.run(self.stop_event, self.activated.emit, self.status_changed.emit)
        except Exception:
            logging.exception('无法启用桌面快捷键')
            self.status_changed.emit(False, 'Ctrl + 空格未启用，请从托盘打开轻记。')

    def stop(self):
        self.stop_event.set()
        if self.backend:
            self.backend.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)


def request_foreground(window_id):
    """Called on the UI thread after a user-initiated global shortcut."""
    if sys.platform == 'win32':
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.SetForegroundWindow(window_id)
