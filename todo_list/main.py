import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional


DATA_FILE = Path(__file__).with_name("todos.json")
DATE_FORMAT = "%Y-%m-%d"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


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


def parse_due(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    try:
        datetime.strptime(value, DATE_FORMAT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD，例如 2026-07-01") from exc

    return value


def load_todos() -> List[Todo]:
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw_items = json.load(file)

    todos = []
    for item in raw_items:
        todos.append(
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
        )
    return todos


def save_todos(todos: Iterable[Todo]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump([asdict(todo) for todo in todos], file, ensure_ascii=False, indent=2)


def next_id(todos: List[Todo]) -> int:
    return max((todo.id for todo in todos), default=0) + 1


def find_todo(todos: List[Todo], todo_id: int) -> Todo:
    for todo in todos:
        if todo.id == todo_id:
            return todo
    raise SystemExit(f"未找到 ID 为 {todo_id} 的待办。")


def is_overdue(todo: Todo) -> bool:
    return bool(todo.due and not todo.done and todo.due < today_text())


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


def filter_todos(todos: List[Todo], args: argparse.Namespace) -> List[Todo]:
    result = todos

    if args.status == "active":
        result = [todo for todo in result if not todo.done]
    elif args.status == "done":
        result = [todo for todo in result if todo.done]

    if args.priority:
        result = [todo for todo in result if todo.priority == args.priority]

    if args.due == "today":
        result = [todo for todo in result if todo.due == today_text()]
    elif args.due == "overdue":
        result = [todo for todo in result if is_overdue(todo)]

    if args.search:
        keyword = args.search.lower()
        result = [
            todo
            for todo in result
            if keyword in todo.title.lower() or keyword in todo.note.lower()
        ]

    return sort_todos(result)


def priority_label(priority: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(priority, priority)


def status_label(todo: Todo) -> str:
    if todo.done:
        return "完成"
    if is_overdue(todo):
        return "逾期"
    return "待办"


def print_todos(todos: List[Todo]) -> None:
    if not todos:
        print("没有符合条件的待办。")
        return

    print(f"{'ID':<4} {'状态':<4} {'优先级':<4} {'截止日期':<12} 事项")
    print("-" * 64)
    for todo in todos:
        due = todo.due or "-"
        print(
            f"{todo.id:<4} {status_label(todo):<4} {priority_label(todo.priority):<4} "
            f"{due:<12} {todo.title}"
        )
        if todo.note:
            print(f"     备注: {todo.note}")


def summarize(todos: List[Todo]) -> None:
    total = len(todos)
    done = sum(todo.done for todo in todos)
    active = total - done
    overdue = sum(is_overdue(todo) for todo in todos)
    due_today = sum(todo.due == today_text() and not todo.done for todo in todos)
    print(f"总计 {total} 项，待办 {active} 项，已完成 {done} 项，今日到期 {due_today} 项，逾期 {overdue} 项。")


def add_todo(args: argparse.Namespace) -> None:
    todos = load_todos()
    todo = Todo(
        id=next_id(todos),
        title=args.title,
        priority=args.priority,
        due=parse_due(args.due),
        note=args.note or "",
        created_at=now_text(),
    )
    todos.append(todo)
    save_todos(todos)
    print(f"已添加待办 #{todo.id}: {todo.title}")


def list_todos(args: argparse.Namespace) -> None:
    todos = load_todos()
    visible = filter_todos(todos, args)
    print_todos(visible)
    print()
    summarize(todos)


def complete_todo(args: argparse.Namespace) -> None:
    todos = load_todos()
    todo = find_todo(todos, args.id)
    todo.done = True
    todo.completed_at = now_text()
    save_todos(todos)
    print(f"已完成待办 #{todo.id}: {todo.title}")


def reopen_todo(args: argparse.Namespace) -> None:
    todos = load_todos()
    todo = find_todo(todos, args.id)
    todo.done = False
    todo.completed_at = None
    save_todos(todos)
    print(f"已重新打开待办 #{todo.id}: {todo.title}")


def delete_todo(args: argparse.Namespace) -> None:
    todos = load_todos()
    todo = find_todo(todos, args.id)
    save_todos([item for item in todos if item.id != args.id])
    print(f"已删除待办 #{todo.id}: {todo.title}")


def edit_todo(args: argparse.Namespace) -> None:
    todos = load_todos()
    todo = find_todo(todos, args.id)

    if args.title is not None:
        todo.title = args.title
    if args.priority is not None:
        todo.priority = args.priority
    if args.due is not None:
        todo.due = parse_due(args.due) if args.due else None
    if args.note is not None:
        todo.note = args.note

    save_todos(todos)
    print(f"已更新待办 #{todo.id}: {todo.title}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="待做事件列表工具")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="新增待办")
    add_parser.add_argument("title", help="事项标题")
    add_parser.add_argument("-p", "--priority", choices=PRIORITY_ORDER.keys(), default="medium", help="优先级")
    add_parser.add_argument("-d", "--due", help="截止日期，格式 YYYY-MM-DD")
    add_parser.add_argument("-n", "--note", help="备注")
    add_parser.set_defaults(func=add_todo)

    list_parser = subparsers.add_parser("list", help="查看待办")
    list_parser.add_argument("-s", "--status", choices=["all", "active", "done"], default="all", help="状态筛选")
    list_parser.add_argument("-p", "--priority", choices=PRIORITY_ORDER.keys(), help="优先级筛选")
    list_parser.add_argument("-d", "--due", choices=["today", "overdue"], help="截止日期筛选")
    list_parser.add_argument("-q", "--search", help="按标题或备注搜索")
    list_parser.set_defaults(func=list_todos)

    done_parser = subparsers.add_parser("done", help="标记完成")
    done_parser.add_argument("id", type=int, help="待办 ID")
    done_parser.set_defaults(func=complete_todo)

    reopen_parser = subparsers.add_parser("reopen", help="重新打开已完成待办")
    reopen_parser.add_argument("id", type=int, help="待办 ID")
    reopen_parser.set_defaults(func=reopen_todo)

    delete_parser = subparsers.add_parser("delete", help="删除待办")
    delete_parser.add_argument("id", type=int, help="待办 ID")
    delete_parser.set_defaults(func=delete_todo)

    edit_parser = subparsers.add_parser("edit", help="编辑待办")
    edit_parser.add_argument("id", type=int, help="待办 ID")
    edit_parser.add_argument("-t", "--title", help="新标题")
    edit_parser.add_argument("-p", "--priority", choices=PRIORITY_ORDER.keys(), help="新优先级")
    edit_parser.add_argument("-d", "--due", help="新截止日期；传空字符串可清除截止日期")
    edit_parser.add_argument("-n", "--note", help="新备注")
    edit_parser.set_defaults(func=edit_todo)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        args = parser.parse_args(["list"])

    args.func(args)


if __name__ == "__main__":
    main()
