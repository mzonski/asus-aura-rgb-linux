import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple, Callable

from ene_controller import ENEController
from utils import RGBColor

logger = logging.getLogger(__name__)


class ENESyncController:
    def __init__(self, devices: Optional[List[Tuple[int, int, str]]] = None) -> None:
        self.devices: List[ENEController] = [
            ENEController(bus, addr, device_name) for bus, addr, device_name in devices
        ]
        logger.info("Sync Controller initialized with %d devices", len(self.devices))

    def execute(self, func: Callable, *args, **kwargs) -> None:
        with ThreadPoolExecutor() as executor:
            list(executor.map(lambda device: func(device, *args, **kwargs), self.devices))

    def set_color(self, color: RGBColor) -> None:
        self.execute(lambda d, c: d.set_color(c), color)

    def set_colors(self, colors: List[RGBColor]) -> None:
        self.execute(lambda d, c: d.set_colors(c), colors)

    def turn_on(self) -> None:
        self.execute(lambda d: d.turn_on())

    def turn_off(self) -> None:
        self.execute(lambda d: d.turn_off())

    def close(self) -> None:
        self.execute(lambda d: d.close())

    def set_direct_mode(self, enabled: bool) -> None:
        self.execute(lambda d, e: d.set_direct_mode(e), enabled)
