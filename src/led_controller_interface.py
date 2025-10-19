from abc import ABC, abstractmethod
from typing import List, Optional

from utils import RGBColor


class LEDControllerInterface(ABC):
    @abstractmethod
    def set_color(self, colors: RGBColor | List[RGBColor]) -> None:
        pass

    @abstractmethod
    def set_static_color(self, colors: RGBColor) -> None:
        pass

    @abstractmethod
    def turn_on(self) -> None:
        pass

    @abstractmethod
    def turn_off(self) -> None:
        pass
