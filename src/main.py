import atexit
import logging
import signal
import sys

from aura_device import AsusAuraLedDevice

logger = logging.getLogger(__name__)


def main():
    closed = False
    aura_device = AsusAuraLedDevice()

    def signal_handler(signum=None, _frame=None):
        logger.info("Received signal %s, shutting down...", signum)
        _cleanup()
        sys.exit(0)

    def _cleanup():
        nonlocal closed, aura_device
        if not aura_device.is_connected():
            closed = True

        if not closed:
            closed = True
            aura_device.disconnect()

    atexit.register(_cleanup)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    with aura_device:
        aura_device.execute_test_sequence()


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    main()
