import logging
import time

from aura_device import AsusAuraLedDevice
from ene_dram import RAMSyncLEDController
from utils import RGBColor

logger = logging.getLogger(__name__)


class SyncedRGBController:
    def __init__(self):
        self.ram_controller = RAMSyncLEDController()
        self.aura_device = AsusAuraLedDevice()
        logger.info("Synced RGB Controller initialized")

    def connect(self) -> None:
        self.aura_device.connect()
        logger.info("All devices connected")

    def disconnect(self) -> None:
        self.aura_device.disconnect()
        self.ram_controller.close()
        logger.info("All devices disconnected")

    def set_color(self, color: RGBColor) -> None:
        [r, g, b] = color
        logger.info("Setting synced color: RGB(%s, %s, %s)", r, g, b)

        self.ram_controller.set_color(r, g, b)
        self.aura_device.set_direct_single_color((r, g, b))

    def turn_on(self) -> None:
        logger.info("Turning on all RGB")
        self.ram_controller.turn_on()
        self.aura_device.turn_on()

    def turn_off(self) -> None:
        logger.info("Turning off all RGB")
        self.aura_device.turn_off()
        self.ram_controller.turn_off()
        self.ram_controller.save_state()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")

    controller = SyncedRGBController()

    try:
        controller.connect()
        controller.turn_on()

        time.sleep(2)

        controller.set_color((15, 0, 0))

    except Exception as e:
        logger.error("Error in main: %s", e)
        raise

    finally:
        controller.disconnect()
        print("\nDone!")
