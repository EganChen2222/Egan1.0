#!/usr/bin/env python3
"""
Scan personalization txt files and insert DELETE commands for selected AIDs.

Default target folder: ./PersoData_1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_EXCLUDED_AIDS = ("A000000151000000",)
SELECT_HEADER = "00A40400"
DELETE_HEADER = "80E40000"


def normalize_hex(value: str) -> str:
    return "".join(re.findall(r"[0-9A-Fa-f]", value)).upper()


def send_payload(line: str) -> str | None:
    match = re.search(r"(?i)/send\s+(.+)$", line)
    if not match:
        return None
    return normalize_hex(match.group(1))


def extract_select_aid(line: str) -> str | None:
    payload = send_payload(line)
    if not payload or not payload.startswith(SELECT_HEADER):
        return None

    if len(payload) < 10:
        return None

    try:
        aid_len = int(payload[8:10], 16)
    except ValueError:
        return None

    aid_start = 10
    aid_end = aid_start + aid_len * 2
    if aid_len == 0 or len(payload) < aid_end:
        return None

    return payload[aid_start:aid_end]


def collect_aids(lines: list[str], excluded_aids: set[str]) -> list[str]:
    seen: set[str] = set()
    aids: list[str] = []

    for line in lines:
        aid = extract_select_aid(line)
        if aid is None or aid in excluded_aids or aid in seen:
            continue
        seen.add(aid)
        aids.append(aid)

    return aids


def build_delete_command(aid: str) -> str:
    aid_bytes = len(aid) // 2
    data_bytes = 2 + aid_bytes
    return f"/send {DELETE_HEADER}{data_bytes:02X}4F{aid_bytes:02X}{aid}"


def existing_send_payloads(lines: list[str]) -> set[str]:
    payloads: set[str] = set()
    for line in lines:
        payload = send_payload(line)
        if payload:
            payloads.add(payload)
    return payloads


def find_insert_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if re.fullmatch(r"\s*ext[- ]auth(?:\s+mac)?\s*", line, flags=re.IGNORECASE):
            return index + 1
    return None


def split_lines_keep_newline(text: str) -> tuple[list[str], str]:
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.splitlines(keepends=True), newline


def process_file(path: Path, excluded_aids: set[str], dry_run: bool) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    lines, newline = split_lines_keep_newline(text)

    aids = collect_aids(lines, excluded_aids)
    if not aids:
        return False, "no selectable AID"

    existing_payloads = existing_send_payloads(lines)
    commands = [
        command
        for aid in aids
        for command in (build_delete_command(aid),)
        if normalize_hex(command[6:]) not in existing_payloads
    ]
    if not commands:
        return False, "DELETE commands already exist"

    insert_index = find_insert_index(lines)
    if insert_index is None:
        return False, "no ext-auth line"

    insert_lines = [f"{command}{newline}" for command in commands]
    if insert_index < len(lines) and lines[insert_index].strip():
        insert_lines.append(newline)

    if not dry_run:
        updated_lines = lines[:insert_index] + insert_lines + lines[insert_index:]
        path.write_text("".join(updated_lines), encoding="utf-8")

    return True, f"inserted {len(commands)} DELETE command(s)"


def choose_folder_with_dialog(initial_dir: Path) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()
    selected = filedialog.askdirectory(initialdir=str(initial_dir), title="Select folder")
    root.destroy()
    return Path(selected) if selected else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insert /send 80E40000 DELETE commands into txt personalization files."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=None,
        help="Folder containing .txt files. Defaults to ./PersoData_1.",
    )
    parser.add_argument(
        "--exclude-aid",
        action="append",
        default=[],
        help="AID to exclude. Can be specified multiple times.",
    )
    parser.add_argument(
        "--choose-folder",
        action="store_true",
        help="Open a folder picker dialog instead of using the default folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent

    if args.choose_folder:
        selected = choose_folder_with_dialog(script_dir)
        if selected is None:
            print("No folder selected or folder dialog is unavailable.", file=sys.stderr)
            return 1
        folder = selected
    else:
        folder = Path(args.folder) if args.folder else script_dir / "PersoData_1"
        if not folder.is_absolute():
            folder = (Path.cwd() / folder).resolve()

    if not folder.is_dir():
        print(f"Folder not found: {folder}", file=sys.stderr)
        return 1

    excluded_aids = {normalize_hex(aid) for aid in DEFAULT_EXCLUDED_AIDS}
    excluded_aids.update(normalize_hex(aid) for aid in args.exclude_aid)

    txt_files = sorted(folder.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {folder}")
        return 0

    changed = 0
    for path in txt_files:
        did_change, message = process_file(path, excluded_aids, args.dry_run)
        changed += int(did_change)
        status = "CHANGE" if did_change else "SKIP"
        print(f"[{status}] {path.name}: {message}")

    action = "would update" if args.dry_run else "updated"
    print(f"Done: {action} {changed}/{len(txt_files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
