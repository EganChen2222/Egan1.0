# -*- coding: utf-8 -*-
"""与读卡器和卡片通信的业务层"""

from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass

from smartcard.Exceptions import CardConnectionException
from smartcard.System import readers

try:
    from .translations import translate
except ImportError:
    from translations import translate


class CardServiceError(Exception):
    """对界面可直接展示的读卡器错误。"""

    def __init__(self, message, english=None):
        super().__init__(message)
        self.english = english or message

    @classmethod
    def from_key(cls, key, **params):
        """错误文案与界面文案共用翻译表。"""
        return cls(translate(key, "zh", **params), translate(key, "en", **params))

    def localized(self, language):
        return self.english if language == "en" else str(self)


@dataclass(frozen=True)
class ApduExchange:
    command: str
    response: str
    status_word: str


@dataclass(frozen=True)
class CommandResult:
    response: str
    status_word: str
    exchanges: tuple[ApduExchange, ...]


class CardService:
    """读卡器枚举、卡片连接、APDU 发送和版本配置读取。"""

    ISD_AID = "A000000003000000"
    GET_DE_APDU = "80CA00DE00"
    GET_CPLC_APDU = "80CA9F7F00"
    PCSC_ERROR_KEYS = {
        "8010000B": "pcsc_8010000b",
        "8010000C": "pcsc_8010000c",
        "80100010": "pcsc_80100010",
        "80100017": "pcsc_80100017",
        "8010001D": "pcsc_8010001d",
        "8010001E": "pcsc_8010001e",
        "80100066": "pcsc_80100066",
        "80100067": "pcsc_80100067",
        "80100068": "pcsc_80100068",
        "80100069": "pcsc_80100069"
    }

    def __init__(self):
        """初始化服务，并创建尚未连接卡片的连接状态。"""
        self.connection = None

    @classmethod
    def readable_error(cls, error: Exception) -> CardServiceError:
        """将 PC/SC 错误码映射到独立翻译表。"""
        match = re.search(r"0x([0-9a-fA-F]{8})", str(error))
        if not match:
            return CardServiceError.from_key("communication_failed")
        code = match.group(1).upper()
        key = cls.PCSC_ERROR_KEYS.get(code, "communication_failed")
        return CardServiceError(
            translate(key, "zh") + translate("pcsc_code", "zh", code=code),
            translate(key, "en") + translate("pcsc_code", "en", code=code),
        )

    def list_readers(self):
        """读取当前系统中的读卡器列表；失败时抛出 CardServiceError。"""
        try:
            return list(readers())
        except Exception as error:
            raise self.readable_error(error) from error

    def disconnect(self):
        """安全断开当前卡片连接；忽略断开过程中的底层清理异常。"""
        if self.connection is not None:
            try:
                self.connection.disconnect()
            except Exception:
                pass
        self.connection = None

    def connect(self, reader) -> str:
        """连接指定读卡器中的卡片，并返回 ATR 十六进制字符串。"""
        self.disconnect()
        try:
            self.connection = reader.createConnection()
            self.connection.connect()
            return self.bytes_to_hex(self.connection.getATR())
        except CardConnectionException as error:
            self.connection = None
            raise self.readable_error(error) from error
        except Exception as error:
            self.connection = None
            raise self.readable_error(error) from error

    def find_readers_with_card(self, reader_list):
        """静默扫描读卡器，返回含有可通信卡片的 (读卡器, ATR) 列表。

        扫描完成后会断开连接；调用方只使用返回的状态展示，或在后续操作中
        对选择的读卡器重新建立正式连接。
        """
        matches = []
        for reader in reader_list:
            try:
                matches.append((reader, self.connect(reader)))
            except CardServiceError:
                # 无卡或接口暂不可用时，不阻断其他读卡器的扫描。
                continue
        self.disconnect()
        return matches

    def select_isd(self) -> CommandResult:
        """选择 GlobalPlatform 主安全域（ISD），并返回完整 APDU 执行记录。"""
        # 使用 Case 3 SELECT，和制卡脚本保持一致，不附加 Le。
        command = f"00A40400{len(self.ISD_AID) // 2:02X}{self.ISD_AID}"
        return self.send_with_get_response(command)

    def read_de(self) -> CommandResult:
        """发送 GET DATA（80CA00DE00）读取卡片 DE 数据。"""
        return self.send_with_get_response(self.GET_DE_APDU)

    def read_cplc(self) -> CommandResult:
        """读取 CPLC；沿用 6Cxx 重发和 61xx 续传处理。"""
        return self.send_with_get_response(self.GET_CPLC_APDU)

    @staticmethod
    def parse_cplc_value(response: str) -> str:
        """接收 42 字节 CPLC Value，或带 9F7F 标签的完整 TLV。"""
        value = "".join(response.split()).upper()
        if not re.fullmatch(r"[0-9A-F]+", value or "") or len(value) % 2:
            raise CardServiceError.from_key("cplc_invalid_hex")
        # 先按原始 Value 长度识别，避免将恰好以 9F7F 开头的 Value 当作标签。
        if len(value) != 84:
            if not value.startswith("9F7F") or len(value) < 6:
                raise CardServiceError.from_key("cplc_invalid_size")
            length = int(value[4:6], 16)
            start = 6
            if length & 0x80:
                count = length & 0x7F
                if count == 0 or count > 2 or len(value) < start + count * 2:
                    raise CardServiceError.from_key("cplc_invalid_length")
                length = int(value[start:start + count * 2], 16)
                start += count * 2
            if length != 42 or len(value) != start + length * 2:
                raise CardServiceError.from_key("cplc_length_mismatch")
            value = value[start:]
        return value

    def send_with_get_response(self, command: str) -> CommandResult:
        """发送命令，并自动处理 ISO 7816 的 6Cxx / 61xx 状态。"""
        exchanges = []
        collected_response = ""
        result = self.send_once(command)
        exchanges.append(result)

        while True:
            if result.status_word.startswith("6C"):
                # 6Cxx：命令 Le 错误，SW2 指出正确 Le。重发当前命令，
                # 例如 80CA00DE00 -> 80CA00DE04。
                if len(result.command) < 10:
                    raise CardServiceError.from_key("apdu_length_failed", status_word=result.status_word)
                corrected_command = result.command[:-2] + result.status_word[2:]
                result = self.send_once(corrected_command)
                exchanges.append(result)
                continue

            collected_response += result.response
            if not result.status_word.startswith("61"):
                break

            # 61xx：命令成功，尚有 xx 字节响应数据，继续 GET RESPONSE。
            result = self.send_once(f"00C00000{result.status_word[2:]}")
            exchanges.append(result)

        return CommandResult(collected_response, result.status_word, tuple(exchanges))

    def send_once(self, command: str) -> ApduExchange:
        """发送一次 APDU，不自动处理状态字续传或重发。"""
        if self.connection is None:
            raise CardServiceError.from_key("no_connected_card")

        command = command.replace(" ", "").upper()
        try:
            data, sw1, sw2 = self.connection.transmit(
                [int(command[index:index + 2], 16) for index in range(0, len(command), 2)]
            )
            return ApduExchange(command, self.bytes_to_hex(data), f"{sw1:02X}{sw2:02X}")
        except Exception as error:
            raise self.readable_error(error) from error

    @staticmethod
    def parse_de_value(response: str) -> str:
        """获取 DE 的 Value；兼容 TLV 响应和直接返回 Value 的卡片。"""
        value = response.replace(" ", "").upper()
        if not value or len(value) % 2 or any(char not in "0123456789ABCDEF" for char in value):
            raise CardServiceError.from_key("de_invalid_hex")
        if value.startswith("DE"):
            if len(value) < 4:
                raise CardServiceError.from_key("de_length_missing")
            first_length = int(value[2:4], 16)
            if first_length < 0x80:
                length, start = first_length, 4
            else:
                length_bytes = first_length & 0x7F
                if length_bytes == 0 or len(value) < 4 + length_bytes * 2:
                    raise CardServiceError.from_key("de_length_incomplete")
                length = int(value[4:4 + length_bytes * 2], 16)
                start = 4 + length_bytes * 2
            end = start + length * 2
            if len(value) < end:
                raise CardServiceError.from_key("de_response_short")
            value = value[start:end]

        if not value or len(value) % 2 or any(char not in "0123456789ABCDEF" for char in value):
            raise CardServiceError.from_key("de_invalid_hex")
        return value

    @staticmethod
    def load_versions(config_file: str, section="Version", byte_length=None):
        """读取版本配置，返回“有效值列表”和“格式无效的配置项”两部分。"""
        if not os.path.exists(config_file):
            raise CardServiceError.from_key("config_missing", config_file=config_file)

        config = configparser.ConfigParser()
        try:
            config.read(config_file, encoding="utf-8")
        except Exception as error:
            raise CardServiceError.from_key("config_read_failed", error=error) from error

        versions, invalid_entries = [], []
        if config.has_section(section):
            for key, raw_value in config.items(section):
                value = raw_value.replace(" ", "").strip().upper()
                if not value:
                    continue
                if len(value) % 2 or any(char not in "0123456789ABCDEF" for char in value) or (byte_length is not None and len(value) != byte_length * 2):
                    invalid_entries.append((key, value))
                else:
                    versions.append(value)
        return versions, invalid_entries

    @staticmethod
    def bytes_to_hex(data) -> str:
        """将 pyscard 返回的字节序列转换为无空格的大写十六进制字符串。"""
        return "".join(f"{byte:02X}" for byte in data)
