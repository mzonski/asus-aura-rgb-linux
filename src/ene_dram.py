import logging
from enum import IntEnum
from typing import List, Optional, Tuple

from smbus3 import SMBus

from utils import RGBColor

logger = logging.getLogger(__name__)


class EneMode(IntEnum):
    OFF = 0
    STATIC = 1


class ENERegister(IntEnum):
    COLORS_DIRECT_V2 = 0x8100
    DIRECT = 0x8020
    MODE = 0x8021
    APPLY = 0x80A0


class ENEWriteMode(IntEnum):
    APPLY_VAL = 0x01
    SAVE_VAL = 0xAA


class ENEController:
    def __init__(self, bus_number: int, address: int) -> None:
        self.bus: SMBus = SMBus(bus_number)
        self.address: int = address
        logger.debug("ENE Controller initialized on bus %s at address 0x%02X", bus_number, address)

    def write_register(self, register: int, value: int) -> None:
        try:
            reg_swapped = ((register << 8) & 0xFF00) | ((register >> 8) & 0x00FF)
            self.bus.write_word_data(self.address, 0x00, reg_swapped)
            self.bus.write_byte_data(self.address, 0x01, value)
            logger.debug("Wrote 0x%02X to register 0x%04X", value, register)
        except Exception as e:
            logger.error("Error writing to register 0x%04X: %s", register, e)
            raise

    def write_register_block(self, register: int, data: List[int]) -> None:
        try:
            reg_swapped = ((register << 8) & 0xFF00) | ((register >> 8) & 0x00FF)
            self.bus.write_word_data(self.address, 0x00, reg_swapped)
            self.bus.write_block_data(self.address, 0x03, data)
            logger.debug("Wrote block to register 0x%04X: %s bytes", register, len(data))
        except Exception as e:
            logger.error("Error writing block to register 0x%04X: %s", register, e)
            raise

    def close(self) -> None:
        try:
            self.bus.close()
            logger.debug("ENE Controller closed")
        except Exception as e:
            logger.error("Error closing ENE Controller: %s", e)


class RAMLEDController:
    def __init__(self, bus_number: int = 6, address: int = 0x71) -> None:
        self.controller: ENEController = ENEController(bus_number, address)
        self.bus_number: int = bus_number
        self.address: int = address
        logger.debug("RAM LED Controller initialized on bus %s at address 0x%02X", bus_number, address)

    def set_color(self, color: RGBColor, led_count: int = 8) -> None:
        [r, g, b] = color
        colors = [(r, g, b)] * led_count
        self._write_colors(colors)
        logger.debug("Set single color RGB(%d, %d, %d) for %d LEDs", r, g, b, led_count)

    def set_colors(self, colors: List[RGBColor]) -> None:
        self._write_colors(colors)
        logger.debug("Set %d individual colors", len(colors))

    def turn_on(self) -> None:
        try:
            self._set_direct_mode(True)
            self._set_mode(EneMode.STATIC)
            logger.debug("RAM LED turned on")
        except Exception as e:
            logger.error("Error turning on RAM LED: %s", e)
            raise

    def turn_off(self) -> None:
        try:
            self._set_direct_mode(False)
            self._set_mode(EneMode.OFF)
            logger.debug("RAM LED turned off")
        except Exception as e:
            logger.error("Error turning off RAM LED: %s", e)
            raise

    def save_state(self) -> None:
        try:
            self.controller.write_register(ENERegister.APPLY, ENEWriteMode.SAVE_VAL)
            logger.debug("RAM LED state saved")
        except Exception as e:
            logger.error("Error saving RAM LED state: %s", e)
            raise

    def close(self) -> None:
        self.controller.close()
        logger.debug("RAM LED Controller closed")

    def _write_colors(self, colors: List[RGBColor]) -> None:
        color_buf: List[int] = []
        for r, g, b in colors:
            color_buf.extend([r, b, g])

        for i in range(0, len(color_buf), 3):
            chunk = color_buf[i : i + 3]
            self.controller.write_register_block(ENERegister.COLORS_DIRECT_V2 + i, chunk)

        self._apply()

    def _set_direct_mode(self, enabled: bool) -> None:
        self.controller.write_register(ENERegister.DIRECT, 1 if enabled else 0)
        self._apply()

    def _set_mode(self, mode: EneMode) -> None:
        self.controller.write_register(ENERegister.MODE, mode)
        self._apply()
        logger.debug("Set mode to %s", mode)

    def _apply(self) -> None:
        self.controller.write_register(ENERegister.APPLY, ENEWriteMode.APPLY_VAL)


class RAMSyncLEDController:
    def __init__(self, ram_configs: Optional[List[Tuple[int, int]]] = None) -> None:
        if ram_configs is None:
            ram_configs = [(6, 0x71), (6, 0x73)]
        self.rams: List[RAMLEDController] = [RAMLEDController(bus, addr) for bus, addr in ram_configs]
        logger.debug("Multi RAM LED Controller initialized with %d RAM modules", len(self.rams))

    def set_color(self, color: RGBColor, led_count: int = 8) -> None:
        for ram in self.rams:
            ram.set_color(color, led_count)

    def set_colors(self, colors: List[RGBColor]) -> None:
        for ram in self.rams:
            ram.set_colors(colors)

    def turn_on(self) -> None:
        for ram in self.rams:
            ram.turn_on()

    def turn_off(self) -> None:
        for ram in self.rams:
            ram.turn_off()

    def save_state(self) -> None:
        for ram in self.rams:
            ram.save_state()

    def close(self) -> None:
        for ram in self.rams:
            ram.close()
