import logging
import threading
import time
from enum import IntEnum
from typing import List, Optional

import hid

from utils import RGBColor

logger = logging.getLogger(__name__)


class CorsairPacketID(IntEnum):
    DIRECT = 0x32
    COMMIT = 0x33
    PORT_STATE = 0x38
    BRIGHTNESS = 0x39
    RESET = 0x37


class CorsairDirectChannel(IntEnum):
    RED = 0x00
    GREEN = 0x01
    BLUE = 0x02


class CorsairPortState(IntEnum):
    SOFTWARE = 0x02
    HARDWARE = 0x01


class CorsairLightingNodeController:
    VENDOR_ID = 0x1B1C
    PRODUCT_ID = 0x0C1A
    WRITE_PACKET_SIZE = 65
    READ_PACKET_SIZE = 17
    READ_TIMEOUT = 15
    LED_COUNT = 4 * 8
    CHANNEL = 0

    def __init__(self) -> None:
        self.device: Optional[hid.Device] = None
        self.keepalive_thread: Optional[threading.Thread] = None
        self.keepalive_running = False
        self.last_commit_time = time.time()
        self.lock = threading.Lock()

    def connect(self) -> None:
        try:
            self.device = hid.Device(vid=self.VENDOR_ID, pid=self.PRODUCT_ID)
            logger.debug("Connected to CORSAIR Lighting Node CORE")
            self.keepalive_running = True
            self.keepalive_thread = threading.Thread(target=self._keepalive_thread, daemon=True)
            self.keepalive_thread.start()
        except OSError as os_err:
            logger.error(
                "Failed to connect to CORSAIR Lighting Node CORE - device not found or access denied: %s", os_err
            )
            raise
        except ValueError as val_err:
            logger.error("Invalid device parameters: %s", val_err)
            raise

    def disconnect(self) -> None:
        self.keepalive_running = False

        if self.keepalive_thread and self.keepalive_thread.is_alive():
            self.keepalive_thread.join(timeout=2)
            if self.keepalive_thread.is_alive():
                logger.warning("Keepalive thread did not terminate within timeout")

        if self.device:
            try:
                self.device.close()
            except OSError as e:
                logger.warning("Error closing device (may already be closed): %s", e)
            finally:
                self.device = None

        logger.debug("CORSAIR Lighting Node CORE disconnected")

    def set_color(self, color: RGBColor) -> None:
        r, g, b = color

        with self.lock:
            self._send_direct(0, self.LED_COUNT, CorsairDirectChannel.RED, [r] * self.LED_COUNT)
            self._send_direct(0, self.LED_COUNT, CorsairDirectChannel.GREEN, [g] * self.LED_COUNT)
            self._send_direct(0, self.LED_COUNT, CorsairDirectChannel.BLUE, [b] * self.LED_COUNT)
            self._send_commit()
            logger.debug("Set direct color RGB(%d, %d, %d)", r, g, b)

    def turn_on(self) -> None:
        self._send_port_state(CorsairPortState.SOFTWARE)
        logger.debug("CORSAIR Lighting Node CORE turned on")

    def turn_off(self) -> None:
        self._send_port_state(CorsairPortState.HARDWARE)
        logger.debug("CORSAIR Lighting Node CORE turned off")

    def close(self) -> None:
        self.disconnect()

    def _send_packet(self, packet_data: List[int]) -> bytes:
        if not self.device:
            raise RuntimeError("Device not connected. Call connect() first.")

        while len(packet_data) < self.WRITE_PACKET_SIZE:
            packet_data.append(0x00)
        packet = packet_data[: self.WRITE_PACKET_SIZE]

        bytes_written = self.device.write(bytes(packet))
        if bytes_written == 0:
            raise OSError("Failed to write data to device")

        try:
            response = self.device.read(self.READ_PACKET_SIZE, timeout=self.READ_TIMEOUT)
            if not response:
                logger.warning("Device returned empty response")
            return response
        except OSError as e:
            logger.error("Failed to read from device: %s", e)
            raise

    def _send_direct(self, start: int, count: int, color_channel: CorsairDirectChannel, color_data: List[int]) -> None:
        if start < 0 or count <= 0 or start + count > self.LED_COUNT:
            raise ValueError(f"Invalid LED range: start={start}, count={count}, max={self.LED_COUNT}")

        packet = [0x00, CorsairPacketID.DIRECT, self.CHANNEL, start, count, color_channel]
        packet.extend(color_data[:count])
        self._send_packet(packet)

    def _send_commit(self) -> None:
        packet = [0x00, CorsairPacketID.COMMIT, 0xFF] + [0x00] * (self.WRITE_PACKET_SIZE - 3)
        self._send_packet(packet)
        self.last_commit_time = time.time()

    def _send_port_state(self, state: CorsairPortState) -> None:
        packet = [0x00, CorsairPacketID.PORT_STATE, self.CHANNEL, state] + [0x00] * (self.WRITE_PACKET_SIZE - 4)
        self._send_packet(packet)

    def _keepalive_thread(self) -> None:
        while self.keepalive_running:
            try:
                if time.time() - self.last_commit_time > 5:
                    with self.lock:
                        self._send_commit()
            except RuntimeError:
                logger.error("Device disconnected in keepalive thread")
                break
            except OSError as os_err:
                logger.error("Communication error in keepalive thread: %s", os_err)

            time.sleep(1)
