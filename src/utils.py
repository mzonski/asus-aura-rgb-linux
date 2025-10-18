from typing import TypeAlias
import logging

RGBColor: TypeAlias = tuple[int, int, int]
DEFAULT_COLOR: RGBColor = (15, 0, 0)
DISABLED_COLOR: RGBColor = (0, 0, 0)

CommandData: TypeAlias = str | bytes | bytearray
logger = logging.getLogger(__name__)


def normalize_command_data(command_data: CommandData, packet_size: int) -> bytes:
    if isinstance(command_data, str):
        data = bytes.fromhex(command_data.replace(" ", ""))
    elif isinstance(command_data, (bytes, bytearray)):
        data = bytes(command_data)
    else:
        raise ValueError(f"Unsupported data type: {type(command_data)}")

    if len(data) < packet_size:
        data = data + b"\x00" * (packet_size - len(data))
    elif len(data) > packet_size:
        data = data[:packet_size]

    return data


def format_hex(data: bytes, trim_zeros: bool = True) -> str:
    if trim_zeros:
        trimmed_data = data.rstrip(b"\x00")
        if not trimmed_data:
            trimmed_data = data[:1] if data else b""
    else:
        trimmed_data = data

    return " ".join(f"{byte:02X}" for byte in trimmed_data)
