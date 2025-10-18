import atexit
import logging
import signal
import sys

from aura_device import AsusAuraLedDevice
from corsair_lighting_node import CorsairLightingNodeController
from ene_dram import RAMSyncLEDController
from utils import RGBColor

logger = logging.getLogger(__name__)


class SyncedRGBController:
    def __init__(self):
        self.ram_controller = RAMSyncLEDController()
        self.corsair_controller = CorsairLightingNodeController()
        self.aura_device = AsusAuraLedDevice()
        self.running = False
        logger.info("Synced RGB Controller initialized")

    def connect(self) -> None:
        self.aura_device.connect()
        self.corsair_controller.connect()
        logger.info("All devices connected")

    def disconnect(self) -> None:
        self.aura_device.disconnect()
        self.corsair_controller.disconnect()
        self.ram_controller.close()
        logger.info("All devices disconnected")

    def set_color(self, color: RGBColor) -> None:
        [r, g, b] = color
        logger.info("Setting synced color: RGB(%s, %s, %s)", r, g, b)
        self.ram_controller.set_color(color)
        self.corsair_controller.set_color(color)
        self.aura_device.set_direct_single_color(color)

    def turn_on(self) -> None:
        logger.info("Turning on all RGB")
        self.ram_controller.turn_on()
        self.corsair_controller.turn_on()
        self.aura_device.turn_on()

    def turn_off(self) -> None:
        logger.info("Turning off all RGB")
        self.aura_device.turn_off()
        self.corsair_controller.turn_off()
        self.ram_controller.turn_off()
        self.ram_controller.save_state()

    def run(self) -> None:
        self.running = True
        try:
            self.connect()
            self.turn_on()
            self.set_color((15, 0, 0))
            logger.info("RGB Controller service running")

            signal.pause()

        except Exception as e:
            logger.error("Error in main loop: %s", e)
            raise

    def stop(self) -> None:
        logger.info("Stopping RGB Controller service")
        self.running = False
        self.turn_off()
        self.disconnect()


def main():
    closed = False

    controller = SyncedRGBController()

    def signal_handler(signum=None, _frame=None):
        logger.info("Received signal %s, shutting down...", signum)
        _cleanup()
        sys.exit(0)

    def _cleanup():
        nonlocal closed, controller

        if not closed:
            closed = True
            controller.stop()

    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        controller.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error("Fatal error: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    main()
