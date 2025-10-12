from enum import IntEnum
from typing import Optional

from utils import RGBColor


def frame_to_hex_string(array: bytes):
    return " ".join(f"{byte:02X}" for byte in array)


class AuraMode(IntEnum):
    OFF = 0
    STATIC = 1
    # BREATHING = 2
    # FLASHING = 3
    # SPECTRUM_CYCLE = 4
    # RAINBOW = 5
    # SPECTRUM_CYCLE_BREATHING = 6
    # CHASE_FADE = 7
    # SPECTRUM_CYCLE_CHASE_FADE = 8
    # CHASE = 9
    # SPECTRUM_CYCLE_CHASE = 10
    # SPECTRUM_CYCLE_WAVE = 11
    # CHASE_RAINBOW_PULSE = 12
    # RANDOM_FLICKER = 13
    # MUSIC = 14
    DIRECT = 0xFF

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()

    @classmethod
    def from_value(cls, value: int) -> "AuraMode":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Invalid mode value: {value}. Valid values: {[m.value for m in cls]}") from exc


class AuraFrameBuilder:
    HEADER = 0xEC
    FRAME_LENGTH = 65

    def __init__(self):
        pass

    def _create_base_frame(self, command, data=None):
        if data is None:
            data = []

        buffer = bytearray([self.HEADER, command] + data)

        while len(buffer) < self.FRAME_LENGTH:
            buffer.append(0x00)

        if len(buffer) > self.FRAME_LENGTH:
            buffer = buffer[: self.FRAME_LENGTH]

        return buffer

    def _get_mask(self, start_led: int, led_count: int) -> int:
        mask = 0
        for i in range(start_led, start_led + led_count):
            if i < 16:  # simplifying to max 16 leds
                mask |= 1 << i
        return mask

    def power_state(self, device_num: int, is_on: bool):
        return self._create_base_frame(0x38, [device_num, int(is_on)])

    def commit(self):
        return self._create_base_frame(0x38, [0x3F, 0x55])

    def effect_mode(self, channel: int, mode: AuraMode, shutdown_effect: bool = False):
        return self._create_base_frame(0x35, [channel, 0x00, int(shutdown_effect), mode])

    def send_color(self, start_led: int, led_count: int, led_data: list, shutdown_effect: bool = False):
        mask = self._get_mask(start_led, led_count)

        if led_data and isinstance(led_data[0], (tuple, list)):
            flat_led_data = []
            for color in led_data:
                flat_led_data.extend(color)
        else:
            flat_led_data = led_data.copy()

        expected_length = led_count * 3
        if len(flat_led_data) < expected_length:
            flat_led_data.extend([0] * (expected_length - len(flat_led_data)))
        elif len(flat_led_data) > expected_length:
            flat_led_data = flat_led_data[:expected_length]

        frame_data = [
            (mask >> 8) & 0xFF,
            mask & 0xFF,
            int(shutdown_effect),
        ]

        frame_data.extend([0] * (3 * start_led))

        frame_data.extend(flat_led_data)

        return self._create_base_frame(0x36, frame_data)

    def create_aura_direct_mode_frame(self, is_gen2: bool, led_count_or_offset: int, rgb_colors: list[RGBColor]):
        protocol_byte = 0x80 if is_gen2 else 0x81

        rgb_data = []
        for r, g, b in rgb_colors:
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            rgb_data.extend([r, g, b])

        frame_data = [protocol_byte, 0x00, led_count_or_offset] + rgb_data
        return self._create_base_frame(0x40, frame_data)

    def direct_mode_single_color(
        self, is_gen2: bool, led_count_or_offset: int, color: RGBColor, num_leds: Optional[int] = None
    ):
        if is_gen2:
            if num_leds is None:
                raise ValueError("num_leds must be specified when is_gen2 is True")
            count = num_leds
        else:
            count = led_count_or_offset

        color_list = [color] * count
        return self.create_aura_direct_mode_frame(is_gen2, led_count_or_offset, color_list)


if __name__ == "__main__":
    builder = AuraFrameBuilder()

    frame = builder.power_state(1, True)
    print(f"Command 0x38: {frame_to_hex_string(frame)}...")

    colors = [(0x00, 0x0F, 0x0F)] * 16
    frame = builder.create_aura_direct_mode_frame(True, 0x10, colors)
    print(f"Gen2 #000f0f x16: {frame_to_hex_string(frame)}...")

    frame = builder.direct_mode_single_color(True, 0x28, (0xFF, 0x00, 0x00), 8)
    print(f"Gen2 single color: {frame_to_hex_string(frame)}...")

    frame = builder.direct_mode_single_color(False, 16, (0xFF, 0x00, 0x00))
    print(f"Gen1 red x8: {frame_to_hex_string(frame)}...")

    frame = builder.effect_mode(0x10, AuraMode.STATIC, False)
    print(f"Send effect: {frame_to_hex_string(frame)}...")

    color_data = [(0xFF, 0, 0), (0, 0xFF, 0), (0, 0, 0xFF)]
    color_frame = builder.send_color(start_led=0, led_count=3, led_data=color_data)
    print(f"Send Color (tuple): {frame_to_hex_string(color_frame)}...")
