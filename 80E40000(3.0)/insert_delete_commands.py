from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

class AIDParser:
    """
    AID解析器
    负责：
        1. 规范化HEX字符串
        2. 提取/send数据
        3. 从SELECT APDU中解析AID
    """

    SELECT_HEADER = "00A40400"

    @staticmethod
    def normalize_hex(value: str) -> str:
        """
        去掉所有非HEX字符并转换为大写
        """
        return "".join(re.findall(r"[0-9A-Fa-f]", value)).upper()

    @staticmethod
    def send_payload(line: str) -> str | None:
        """
        从一行中提取/send后面的APDU数据

        示例：
        /send 00A4040008A0000003330101
        ↓
        00A4040008A0000003330101
        """

        match = re.search(r"(?i)/send\s+(.+)$", line)

        if not match:
            return None

        return AIDParser.normalize_hex(match.group(1))

    @staticmethod
    def extract_select_aid(line: str) -> str | None:
        """
        从SELECT APDU中提取AID

        示例：
        /send 00A4040008A0000003330101
        ↓
        A0000003330101
        """

        payload = AIDParser.send_payload(line)

        if payload is None:
            return None

        if not payload.startswith(AIDParser.SELECT_HEADER):
            return None

        # 至少要有 CLA INS P1 P2 Lc
        if len(payload) < 10:
            return None

        try:
            aid_length = int(payload[8:10], 16)
        except ValueError:
            return None

        if aid_length == 0:
            return None

        aid_start = 10
        aid_end = aid_start + aid_length * 2

        if len(payload) < aid_end:
            return None

        return payload[aid_start:aid_end]

    @staticmethod
    def collect_aids(lines: list[str], excluded_aids: set[str] | None = None) -> list[str]:
        """
        从TXT所有内容中收集AID

        Parameters
        ----------
        lines : list[str]
            TXT所有行

        excluded_aids : set[str]
            需要排除的AID

        Returns
        -------
        list[str]
            去重后的AID列表
        """

        if excluded_aids is None:
            excluded_aids = set()

        aids = []
        seen = set()

        for line in lines:

            aid = AIDParser.extract_select_aid(line)

            if aid is None:
                continue

            if aid in excluded_aids:
                continue

            if aid in seen:
                continue

            seen.add(aid)
            aids.append(aid)

        return aids

class DeleteCommandBuilder:
    """
    DELETE指令构造器

    负责：
        1. 根据AID生成DELETE APDU
        2. 获取文件中已有的APDU数据
        3. 判断DELETE命令是否已存在
    """

    DELETE_HEADER = "80E40000"

    @classmethod
    def build_delete_command(cls, aid: str) -> str:
        """
        根据AID生成DELETE命令

        示例：
        A0000003330101

        ->
        /send 80E40000094F07A0000003330101
        """

        aid_bytes = len(aid) // 2

        # Data = 4F + Len + AID
        data_length = aid_bytes + 2

        return (
            f"/send "
            f"{cls.DELETE_HEADER}"
            f"{data_length:02X}"
            f"4F"
            f"{aid_bytes:02X}"
            f"{aid}"
        )

    @staticmethod
    def existing_payloads(lines: list[str]) -> set[str]:
        """
        获取TXT中已有的所有/send APDU数据

        返回：
        {
            "00A4040008A0000003330101",
            "80E40000094F07A0000003330101",
            ...
        }
        """

        payloads = set()

        for line in lines:

            payload = AIDParser.send_payload(line)

            if payload:
                payloads.add(payload)

        return payloads

    @classmethod
    def command_exists(cls, aid: str, existing_payloads: set[str]) -> bool:
        """
        判断指定AID对应的DELETE命令是否已经存在
        """

        command = cls.build_delete_command(aid)

        payload = AIDParser.normalize_hex(command[6:])

        return payload in existing_payloads

    @classmethod
    def build_commands(
            cls,
            aids: list[str],
            existing_payloads: set[str]
    ) -> list[str]:
        """
        根据AID列表生成所有需要插入的DELETE命令

        已存在的不再生成。
        """

        commands = []

        for aid in aids:

            if cls.command_exists(aid, existing_payloads):
                continue

            commands.append(
                cls.build_delete_command(aid)
            )

        return commands

class FolderProcessor:

    def __init__(self,
                 excluded_aids=None,
                 dry_run=False):

        self.excluded_aids = excluded_aids or set()
        self.dry_run = dry_run

    @staticmethod
    def split_lines_keep_newline(text: str):

        newline = "\r\n" if "\r\n" in text else "\n"

        return text.splitlines(keepends=True), newline

    @staticmethod
    def find_insert_index(lines):

        for index, line in enumerate(lines):

            if re.fullmatch(
                    r"\s*ext[- ]auth(?:\s+mac)?\s*",
                    line,
                    flags=re.IGNORECASE):

                return index + 1

        return None

    def process_file(self,
                     input_path: Path,
                     output_path: Path):

        text = input_path.read_text(
            encoding="utf-8"
        )

        lines, newline = self.split_lines_keep_newline(text)

        aids = AIDParser.collect_aids(
            lines,
            self.excluded_aids
        )

        if not aids:
            return False, "no selectable AID"

        existing_payloads = DeleteCommandBuilder.existing_payloads(lines)

        commands = DeleteCommandBuilder.build_commands(
            aids,
            existing_payloads
        )

        if not commands:
            return False, "DELETE commands already exist"

        insert_index = self.find_insert_index(lines)

        if insert_index is None:
            return False, "no ext-auth line"

        insert_lines = [
            f"{cmd}{newline}"
            for cmd in commands
        ]

        if insert_index < len(lines) and lines[insert_index].strip():
            insert_lines.append(newline)

        updated_lines = (
                lines[:insert_index]
                + insert_lines
                + lines[insert_index:]
        )

        if self.dry_run:
            return True, f"would insert {len(commands)} DELETE command(s)"

        output_path.write_text(
            "".join(updated_lines),
            encoding="utf-8"
        )

        return True, f"inserted {len(commands)} DELETE command(s)"

    def process_folder(
            self,
            input_folder: str | Path,
            output_folder: str | Path
    ):

        input_folder = Path(input_folder)
        output_folder = Path(output_folder)

        if not input_folder.exists():
            raise FileNotFoundError(
                f"输入目录不存在：{input_folder}"
            )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        txt_files = sorted(input_folder.glob("*.txt"))

        if not txt_files:
            print("输入目录没有txt文件")
            return

        changed = 0

        for input_path in txt_files:

            output_path = output_folder / input_path.name

            did_change, message = self.process_file(
                input_path,
                output_path
            )

            if did_change:
                changed += 1

            status = "CHANGE" if did_change else "SKIP"

            print(f"[{status}] {input_path.name}: {message}")

        action = (
            "would update"
            if self.dry_run
            else "updated"
        )

        print(
            f"\nDone: {action} {changed}/{len(txt_files)} file(s)."
        )

def choose_folder_with_dialog(title: str) -> Path | None:
    """
    打开文件夹选择框
    """

    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title=title)

    root.destroy()

    if folder:
        return Path(folder)

    return None

def main():

    input_folder = Path(
        r"D:\Data\PersoData"
    )

    output_folder = Path(
        r"D:\Data\Output"
    )

    processor = FolderProcessor(
        excluded_aids={
            AIDParser.normalize_hex(
                "A000000151000000"
            )
        },
        dry_run=False
    )

    processor.process_folder(
        input_folder,
        output_folder
    )


if __name__ == "__main__":
    main()