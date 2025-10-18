import logging
import time
from typing import List, Optional

from usb.core import Device, USBError, USBTimeoutError
from usb.core import find as find_device
from usb.util import dispose_resources

from aura_frame_builder import AuraFrameBuilder, AuraMode, RGBColor
from utils import CommandData, format_hex, normalize_command_data

fb = AuraFrameBuilder()
logger = logging.getLogger(__name__)


class KernelDriverManager:
    def __init__(self, device: Device) -> None:
        self.device: Device = device
        self.detached_interfaces: List[int] = []

    def detach_interfaces(self) -> None:
        for interface in self.device.get_active_configuration():
            interface_number = interface.bInterfaceNumber

            try:
                if not self.device.is_kernel_driver_active(interface_number):
                    continue
                logger.debug("Detaching kernel driver from interface: %s", interface_number)
                self.device.detach_kernel_driver(interface_number)
                self.detached_interfaces.append(interface_number)
            except USBError as e:
                logger.error("Could not detach kernel driver from interface: %s. %s", interface_number, e)
                raise

    def reattach_interfaces(self) -> None:
        for interface_number in self.detached_interfaces:
            try:
                self.device.attach_kernel_driver(interface_number)
                logger.debug("Reattached kernel driver to interface: %s", interface_number)
            except USBError as e:
                logger.error("Error reattaching kernel driver %s", e)
            except NotImplementedError:
                pass


class USBDeviceConnection:
    def __init__(self, vendor_id: int, product_id: int) -> None:
        self.vendor_id: int = vendor_id
        self.product_id: int = product_id
        self.device: Optional[Device] = None
        self.interface: Optional[int] = None
        self.kernel_manager: Optional[KernelDriverManager] = None

    def open(self) -> None:
        if self.device:
            logger.error("Device is already open")
            return

        device = find_device(idVendor=self.vendor_id, idProduct=self.product_id)

        if device is None:
            raise RuntimeError(f"Device not found (VID:{self.vendor_id:04X} PID:{self.product_id:04X})")

        self.device = device
        self.kernel_manager = KernelDriverManager(self.device)
        self.kernel_manager.detach_interfaces()

        try:
            self.device.set_configuration(1)
            logger.debug("Set device configuration")
        except USBError as e:
            logger.error("Could not set configuration: %s", e)

        logger.debug("Device opened successfully: Bus %s, Address %s", self.device.bus, self.device.address)

    def close(self) -> None:
        if not self.device:
            logger.warning("Device is already closed")
            return

        dispose_resources(self.device)
        if self.kernel_manager:
            self.kernel_manager.reattach_interfaces()

        self.device = None
        self.interface = None
        logger.debug("Device closed successfully")

    def is_open(self) -> bool:
        return self.device is not None

    def get_device(self) -> Device:
        if not self.device:
            raise RuntimeError("Device not opened")
        return self.device


class AsusAuraLedDevice:
    VENDOR_ID: int = 0x0B05
    PRODUCT_ID: int = 0x19AF
    PACKET_SIZE: int = 65
    DEFAULT_TIMEOUT: int = 1500

    def __init__(self, throttle: bool = False) -> None:
        self._connection: USBDeviceConnection = USBDeviceConnection(self.VENDOR_ID, self.PRODUCT_ID)
        self._throttle: bool = throttle

    def __enter__(self) -> "AsusAuraLedDevice":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.is_connected():
            self.disconnect()

    def connect(self) -> None:
        self._connection.open()

    def disconnect(self) -> None:
        self._connection.close()

    def send(self, command_data: CommandData, command_id: Optional[int] = None) -> int:
        if not self._connection.is_open():
            raise RuntimeError("Device not opened")
        try:
            data = normalize_command_data(command_data, self.PACKET_SIZE)
            if command_id is not None:
                logger.debug("Sending command (%s): %s", command_id, format_hex(data))
            else:
                logger.debug("Sending command: %s", format_hex(data))

            read_bytes = self._connection.get_device().ctrl_transfer(
                bmRequestType=0x21,
                bRequest=0x09,
                wValue=0x02EC,
                wIndex=2,
                data_or_wLength=data,
                timeout=self.DEFAULT_TIMEOUT,
            )
            if self._throttle:
                time.sleep(1.0)
            return read_bytes

        except USBTimeoutError:
            logger.error("USB timeout during command send")
            raise
        except Exception as e:
            logger.error("Error sending command: %s", e)
            raise

    def is_connected(self) -> bool:
        return self._connection.is_open()

    def toggle_throttle(self):
        self._throttle = not self._throttle

    def turn_off(self) -> None:
        self.send(fb.commit())
        self.send(fb.power_state(0, False))
        self.send(fb.power_state(1, False))

    def turn_on(self) -> None:
        self.send(fb.power_state(0, True))
        self.send(fb.power_state(1, True))

    def set_direct_single_color(self, color: RGBColor):
        self.send(fb.commit())
        self.turn_on()

        self.send(fb.effect_mode(0x01, AuraMode.DIRECT, False))
        self.send(fb.effect_mode(0x10, AuraMode.DIRECT, False))
        self.send(fb.effect_mode(0x11, AuraMode.DIRECT, False))
        self.send(fb.effect_mode(0x12, AuraMode.DIRECT, False))

        self.send(fb.direct_mode_single_color(False, 16, color))
        self.send(fb.direct_mode_single_color(True, 0x28, color, 8))
        self.send(fb.direct_mode_single_color(True, 0x48, color, 8))
        self.send(fb.direct_mode_single_color(True, 0x68, color, 8))

    def execute_test_sequence(self) -> None:
        try:
            self.turn_off()
            time.sleep(1)
            self.set_direct_single_color((15, 0, 0))
        except Exception as e:
            logger.error("Error in test sequence: %s", e)
            raise
