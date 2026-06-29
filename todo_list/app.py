import json
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Iterable, List, Optional


DATA_FILE = Path(__file__).with_name("todos.json")
DATE_FORMAT = "%Y-%m-%d"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_TEXT = {"high": "高", "medium": "中", "low": "低"}
PRIORITY_VALUE = {"高": "high", "中": "medium", "低": "low"}


@dataclass
class Todo:
    id: int
    title: str
    done: bool = False
    priority: str = "medium"
    due: Optional[str] = None
    note: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None


def today_text() -> str:
    return date.today().strftime(DATE_FORMAT)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_due(value: str) -> Optional[str]:
    value = value.strip()
    if not value:
        return None
    try:
        datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValueError("截止日期格式应为 YYYY-MM-DD，例如 2026-07-01")
    return value


def load_todos() -> List[Todo]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw_items = json.load(file)
    return [
        Todo(
            id=int(item["id"]),
            title=item["title"],
            done=bool(item.get("done", False)),
            priority=item.get("priority", "medium"),
            due=item.get("due"),
            note=item.get("note", ""),
            created_at=item.get("created_at", ""),
            completed_at=item.get("completed_at"),
        )
        for item in raw_items
    ]


def save_todos(todos: Iterable[Todo]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump([asdict(todo) for todo in todos], file, ensure_ascii=False, indent=2)


def next_id(todos: List[Todo]) -> int:
    return max((todo.id for todo in todos), default=0) + 1


def is_overdue(todo: Todo) -> bool:
    return bool(todo.due and not todo.done and todo.due < today_text())


def status_text(todo: Todo) -> str:
    if todo.done:
        return "完成"
    if is_overdue(todo):
        return "逾期"
    return "待办"


def sort_todos(todos: Iterable[Todo]) -> List[Todo]:
    return sorted(
        todos,
        key=lambda todo: (
            todo.done,
            PRIORITY_ORDER.get(todo.priority, 1),
            todo.due or "9999-12-31",
            todo.id,
        ),
    )


class TodoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("待做事件列表")
        self.geometry("980x640")
        self.minsize(820, 540)

        self.todos = load_todos()
        self.selected_id = None

        self.status_filter = tk.StringVar(value="全部")
        self.priority_filter = tk.StringVar(value="全部")
        self.due_filter = tk.StringVar(value="全部")
        self.search_var = tk.StringVar()

        self.title_var = tk.StringVar()
        self.priority_var = tk.StringVar(value="中")
        self.due_var = tk.StringVar()
        self.note_text = None

        self.configure_style()
        self.build_layout()
        self.refresh_table()

    def configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f7f9")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f6f7f9", foreground="#20242a", font=("Microsoft YaHei UI", 10))
        style.configure("Panel.TLabel", background="#ffffff", foreground="#20242a", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", background="#f6f7f9", foreground="#111827", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Summary.TLabel", background="#f6f7f9", foreground="#4b5563", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(10, 6))
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=(12, 7))
        style.configure("Treeview", font=("Microsoft YaHei UI", 10), rowheight=32)
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"))

    def build_layout(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(header, text="待做事件列表", style="Title.TLabel").pack(side=tk.LEFT)
        self.summary_label = ttk.Label(header, text="", style="Summary.TLabel")
        self.summary_label.pack(side=tk.RIGHT, pady=(8, 0))

        content = ttk.Frame(root)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=2)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(1, weight=1)

        filters = ttk.Frame(content)
        filters.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        filters.columnconfigure(7, weight=1)

        ttk.Label(filters, text="状态").grid(row=0, column=0, padx=(0, 6))
        ttk.Combobox(filters, textvariable=self.status_filter, values=["全部", "待办", "完成"], width=8, state="readonly").grid(row=0, column=1, padx=(0, 12))
        ttk.Label(filters, text="优先级").grid(row=0, column=2, padx=(0, 6))
        ttk.Combobox(filters, textvariable=self.priority_filter, values=["全部", "高", "中", "低"], width=8, state="readonly").grid(row=0, column=3, padx=(0, 12))
        ttk.Label(filters, text="日期").grid(row=0, column=4, padx=(0, 6))
        ttk.Combobox(filters, textvariable=self.due_filter, values=["全部", "今日到期", "已逾期"], width=10, state="readonly").grid(row=0, column=5, padx=(0, 12))
        ttk.Label(filters, text="搜索").grid(row=0, column=6, padx=(0, 6))
        search_entry = ttk.Entry(filters, textvariable=self.search_var)
        search_entry.grid(row=0, column=7, sticky="ew")

        for var in (self.status_filter, self.priority_filter, self.due_filter, self.search_var):
            var.trace_add("write", lambda *_: self.refresh_table())

        table_frame = ttk.Frame(content)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("status", "priority", "due", "title")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.table.heading("status", text="状态")
        self.table.heading("priority", text="优先级")
        self.table.heading("due", text="截止日期")
        self.table.heading("title", text="事项")
        self.table.column("status", width=72, anchor=tk.CENTER, stretch=False)
        self.table.column("priority", width=72, anchor=tk.CENTER, stretch=False)
        self.table.column("due", width=110, anchor=tk.CENTER, stretch=False)
        self.table.column("title", width=380, anchor=tk.W)
        self.table.grid(row=0, column=0, sticky="nsew")
        self.table.bind("<<TreeviewSelect>>", self.on_select)
        self.table.bind("<Double-1>", lambda _event: self.toggle_done())

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        form = ttk.Frame(content, style="Panel.TFrame", padding=16)
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(0, weight=1)

        ttk.Label(form, text="事项标题", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.title_var).grid(row=1, column=0, sticky="ew", pady=(4, 12))

        row = ttk.Frame(form, style="Panel.TFrame")
        row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        ttk.Label(row, text="优先级", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(row, text="截止日期", style="Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Combobox(row, textvariable=self.priority_var, values=["高", "中", "低"], state="readonly").grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Entry(row, textvariable=self.due_var).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(4, 0))

        ttk.Label(form, text="备注", style="Panel.TLabel").grid(row=3, column=0, sticky="w")
        self.note_text = tk.Text(form, height=8, wrap=tk.WORD, font=("Microsoft YaHei UI", 10), relief=tk.SOLID, borderwidth=1)
        self.note_text.grid(row=4, column=0, sticky="nsew", pady=(4, 14))
        form.rowconfigure(4, weight=1)

        ttk.Button(form, text="新增", style="Accent.TButton", command=self.add_todo).grid(row=5, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(form, text="保存修改", command=self.update_todo).grid(row=6, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(form, text="完成 / 重新打开", command=self.toggle_done).grid(row=7, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(form, text="删除", command=self.delete_todo).grid(row=8, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(form, text="清空表单", command=self.clear_form).grid(row=9, column=0, sticky="ew")

    def visible_todos(self) -> List[Todo]:
        result = list(self.todos)
        if self.status_filter.get() == "待办":
            result = [todo for todo in result if not todo.done]
        elif self.status_filter.get() == "完成":
            result = [todo for todo in result if todo.done]

        if self.priority_filter.get() != "全部":
            result = [todo for todo in result if PRIORITY_TEXT.get(todo.priority) == self.priority_filter.get()]

        if self.due_filter.get() == "今日到期":
            result = [todo for todo in result if todo.due == today_text() and not todo.done]
        elif self.due_filter.get() == "已逾期":
            result = [todo for todo in result if is_overdue(todo)]

        keyword = self.search_var.get().strip().lower()
        if keyword:
            result = [
                todo
                for todo in result
                if keyword in todo.title.lower() or keyword in todo.note.lower()
            ]
        return sort_todos(result)

    def refresh_table(self) -> None:
        for item_id in self.table.get_children():
            self.table.delete(item_id)

        for todo in self.visible_todos():
            self.table.insert(
                "",
                tk.END,
                iid=str(todo.id),
                values=(
                    status_text(todo),
                    PRIORITY_TEXT.get(todo.priority, todo.priority),
                    todo.due or "-",
                    todo.title,
                ),
            )

        total = len(self.todos)
        done = sum(todo.done for todo in self.todos)
        overdue = sum(is_overdue(todo) for todo in self.todos)
        due_today = sum(todo.due == today_text() and not todo.done for todo in self.todos)
        self.summary_label.configure(
            text=f"总计 {total} 项｜待办 {total - done} 项｜已完成 {done} 项｜今日到期 {due_today} 项｜逾期 {overdue} 项"
        )

    def selected_todo(self) -> Optional[Todo]:
        selection = self.table.selection()
        if not selection:
            return None
        todo_id = int(selection[0])
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def on_select(self, _event=None) -> None:
        todo = self.selected_todo()
        if not todo:
            return
        self.selected_id = todo.id
        self.title_var.set(todo.title)
        self.priority_var.set(PRIORITY_TEXT.get(todo.priority, "中"))
        self.due_var.set(todo.due or "")
        self.note_text.delete("1.0", tk.END)
        self.note_text.insert("1.0", todo.note)

    def form_values(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("缺少标题", "请先输入事项标题。")
            return None
        try:
            due = validate_due(self.due_var.get())
        except ValueError as exc:
            messagebox.showwarning("日期格式错误", str(exc))
            return None
        note = self.note_text.get("1.0", tk.END).strip()
        priority = PRIORITY_VALUE.get(self.priority_var.get(), "medium")
        return title, priority, due, note

    def add_todo(self) -> None:
        values = self.form_values()
        if not values:
            return
        title, priority, due, note = values
        self.todos.append(
            Todo(
                id=next_id(self.todos),
                title=title,
                priority=priority,
                due=due,
                note=note,
                created_at=now_text(),
            )
        )
        save_todos(self.todos)
        self.clear_form()
        self.refresh_table()

    def update_todo(self) -> None:
        todo = self.selected_todo()
        if not todo:
            messagebox.showinfo("未选择事项", "请先在左侧列表选择一条待办。")
            return
        values = self.form_values()
        if not values:
            return
        todo.title, todo.priority, todo.due, todo.note = values
        save_todos(self.todos)
        self.refresh_table()

    def toggle_done(self) -> None:
        todo = self.selected_todo()
        if not todo:
            messagebox.showinfo("未选择事项", "请先在左侧列表选择一条待办。")
            return
        todo.done = not todo.done
        todo.completed_at = now_text() if todo.done else None
        save_todos(self.todos)
        self.refresh_table()

    def delete_todo(self) -> None:
        todo = self.selected_todo()
        if not todo:
            messagebox.showinfo("未选择事项", "请先在左侧列表选择一条待办。")
            return
        if not messagebox.askyesno("确认删除", f"确定删除「{todo.title}」吗？"):
            return
        self.todos = [item for item in self.todos if item.id != todo.id]
        save_todos(self.todos)
        self.clear_form()
        self.refresh_table()

    def clear_form(self) -> None:
        self.selected_id = None
        self.table.selection_remove(self.table.selection())
        self.title_var.set("")
        self.priority_var.set("中")
        self.due_var.set("")
        self.note_text.delete("1.0", tk.END)


if __name__ == "__main__":
    TodoApp().mainloop()
