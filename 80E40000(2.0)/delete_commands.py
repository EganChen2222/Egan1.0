import re
from collections import OrderedDict


class Config:
    """
    全局配置
    """

    # 默认排除的AID（Card Manager）
    DEFAULT_EXCLUDED_AIDS = {
        "A000000151000000"
    }

    # SELECT命令头
    SELECT_HEADER = "00A40400"

    # DELETE命令头
    DELETE_HEADER = "80E40000"

    # txt文件编码
    ENCODING = "utf-8"

    # ext-auth关键字
    EXT_AUTH_PATTERN = re.compile(
        r"\s*ext[- ]auth(?:\s+mac)?\s*",
        flags=re.IGNORECASE
    )


class AIDParser:
    """
    AID解析器

    功能：
        ① 清洗HEX字符串
        ② 提取/send后的APDU
        ③ 解析SELECT AID
        ④ 收集整个文件中的AID
    """

    def normalize_hex(self, value: str) -> str:
        """
        去掉所有空格、Tab等，仅保留HEX字符。

        例如：

        00 A4 04 00 07 A0 00 00 00 04 10 10

        →

        00A4040007A0000000041010
        """

        return "".join(
            re.findall(r"[0-9A-Fa-f]", value)
        ).upper()

    def get_send_payload(self, line: str) -> str | None:
        """
        获取/send后面的HEX数据。

        输入：

        /send 00A4040007A0000000041010

        返回：

        00A4040007A0000000041010
        """

        match = re.search(
            r"(?i)/send\s+(.+)$",
            line
        )

        if not match:
            return None

        return self.normalize_hex(match.group(1))

    def extract_select_aid(self, line: str) -> str | None:
        """
        从一行SELECT命令中提取AID。

        输入：

        /send 00A4040007A0000000041010

        返回：

        A0000000041010
        """

        payload = self.get_send_payload(line)

        if payload is None:
            return None

        if not payload.startswith(Config.SELECT_HEADER):
            return None

        if len(payload) < 10:
            return None

        try:
            aid_length = int(payload[8:10], 16)
        except ValueError:
            return None

        if aid_length <= 0:
            return None

        aid_begin = 10
        aid_end = aid_begin + aid_length * 2

        if len(payload) < aid_end:
            return None

        return payload[aid_begin:aid_end]

    def collect_aids(
            self,
            lines: list[str],
            excluded_aids: set[str]
    ) -> list[str]:
        """
        收集整个文件中的AID。

        功能：

        ① 自动去重

        ② 保持首次出现顺序

        ③ 排除主控AID

        返回：

        [
            "A0000000041010",
            "325041592E5359532E4444463031",
            ...
        ]
        """

        ordered = OrderedDict()

        for line in lines:

            aid = self.extract_select_aid(line)

            if aid is None:
                continue

            if aid in excluded_aids:
                continue

            if aid not in ordered:
                ordered[aid] = None

        return list(ordered.keys())


class DeleteCommandBuilder:
    """
    DELETE命令生成器
    """

    def calculate_aid_length(self, aid: str) -> int:
        """
        返回AID长度(Byte)

        A0000000041010

        →

        7
        """

        return len(aid) // 2

    def calculate_lc(self, aid: str) -> int:
        """
        计算DELETE命令Lc

        Lc = Tag(1) + Length(1) + AID

        即：

        AID长度 + 2
        """

        return self.calculate_aid_length(aid) + 2

    def build_delete_command(self, aid: str) -> str:
        """
        根据AID生成DELETE命令。

        输入：

        A0000000041010

        返回：

        /send 80E40000094F07A0000000041010
        """

        aid_length = self.calculate_aid_length(aid)

        lc = self.calculate_lc(aid)

        return (
            f"/send "
            f"{Config.DELETE_HEADER}"
            f"{lc:02X}"
            f"4F"
            f"{aid_length:02X}"
            f"{aid}"
        )

    def build_delete_commands(
            self,
            aids: list[str]
    ) -> list[str]:
        """
        批量生成DELETE命令。
        """

        commands = []

        for aid in aids:
            commands.append(
                self.build_delete_command(aid)
            )

        return commands
