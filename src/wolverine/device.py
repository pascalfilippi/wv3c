"""Low-level hidraw device discovery and communication."""

import fcntl
import os
import struct
import time

from . import VENDOR_ID, PRODUCT_ID

XBOX_PRODUCT_ID = 0x0A3F   # controller in Xbox mode — different protocol, not usable here
HIDIOCGRAWINFO = 0x80084803
FEATURE_REPORT_ID = 0x04
RAZER_REPORT_LEN = 90

# ioctl numbers for HID feature reports
def _hidiocsfeature(length: int) -> int:
    return 0xC0004806 | (length << 16)

def _hidiocgfeature(length: int) -> int:
    return 0xC0004807 | (length << 16)


def check_device_mode() -> str | None:
    """Detect whether the Wolverine V3 Pro is connected in PC or Xbox mode.

    Reads /sys/bus/usb/devices/ first (world-readable, no udev rule required),
    then falls back to scanning hidraw nodes for environments where sysfs is
    unavailable.

    Returns:
        'pc'   — found in normal PC mode (ready to use)
        'xbox' — found in Xbox mode (1532:0a3f); needs to be switched
        None   — not found at all
    """
    import glob as _glob

    # sysfs scan: no permissions needed, works even when the Xbox-mode hidraw
    # node is inaccessible (no udev rule for 1532:0a3f).
    for vendor_file in _glob.glob('/sys/bus/usb/devices/*/idVendor'):
        dev_dir = os.path.dirname(vendor_file)
        try:
            with open(vendor_file) as f:
                vid = int(f.read().strip(), 16)
            if vid != VENDOR_ID:
                continue
            with open(os.path.join(dev_dir, 'idProduct')) as f:
                pid = int(f.read().strip(), 16)
            if pid == PRODUCT_ID:
                return 'pc'
            if pid == XBOX_PRODUCT_ID:
                return 'xbox'
        except (OSError, ValueError):
            continue

    # Fallback: scan hidraw nodes directly
    for i in range(20):
        path = f"/dev/hidraw{i}"
        if not os.path.exists(path):
            continue
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            try:
                buf = bytearray(8)
                fcntl.ioctl(fd, HIDIOCGRAWINFO, buf)
                _, vendor, product = struct.unpack("<Ihh", buf)
                pid = product & 0xFFFF
                if vendor == VENDOR_ID:
                    if pid == PRODUCT_ID:
                        return 'pc'
                    if pid == XBOX_PRODUCT_ID:
                        return 'xbox'
            finally:
                os.close(fd)
        except (OSError, PermissionError):
            continue
    return None


def find_device() -> str | None:
    """Find the hidraw device path for the Wolverine V3 Pro controller."""
    for i in range(20):
        path = f"/dev/hidraw{i}"
        if not os.path.exists(path):
            continue
        try:
            fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
            try:
                buf = bytearray(8)
                fcntl.ioctl(fd, HIDIOCGRAWINFO, buf)
                _, vendor, product = struct.unpack("<Ihh", buf)
                if vendor == VENDOR_ID and (product & 0xFFFF) == PRODUCT_ID:
                    return path
            finally:
                os.close(fd)
        except (OSError, PermissionError):
            continue
    return None


class WolverineDevice:
    """Manages a connection to the Wolverine V3 Pro controller."""

    def __init__(self, path: str | None = None):
        self.path = path or find_device()
        if self.path is None:
            raise FileNotFoundError("Wolverine V3 Pro controller not found")
        self._fd: int | None = None

    def open(self):
        if self._fd is not None:
            return
        self._fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    def _build_report(self, cmd_class: int, cmd_id: int,
                      data_size: int, args: list[int],
                      tid: int = 0x1F) -> bytes:
        report = bytearray(RAZER_REPORT_LEN)
        report[0] = 0x00
        report[1] = tid
        report[5] = data_size
        report[6] = cmd_class
        report[7] = cmd_id
        for i, b in enumerate(args[:80]):
            report[8 + i] = b
        crc = 0
        for i in range(2, 88):
            crc ^= report[i]
        report[88] = crc
        return bytes(report)

    def send_command(self, cmd_class: int, cmd_id: int,
                     data_size: int, args: list[int],
                     delay: float = 0.15) -> tuple[int, bytes] | None:
        """Send a Razer command and read the response.

        Returns (status, data) or None on failure.
        Status: 0x00=New, 0x02=OK, 0x03=NotSupported, 0x05=WrongMode
        """
        if self._fd is None:
            raise RuntimeError("Device not open")

        report = self._build_report(cmd_class, cmd_id, data_size, args)
        feature_buf = bytes([FEATURE_REPORT_ID]) + report

        try:
            fcntl.ioctl(self._fd, _hidiocsfeature(len(feature_buf)), feature_buf)
        except OSError:
            return None

        time.sleep(delay)

        try:
            resp_buf = bytearray([FEATURE_REPORT_ID]) + bytearray(RAZER_REPORT_LEN)
            fcntl.ioctl(self._fd, _hidiocgfeature(len(resp_buf)), resp_buf)
            resp = bytes(resp_buf[1:])
            status = resp[0]
            data_len = resp[5]
            data = resp[8:8 + data_len] if data_len > 0 else b""
            return (status, data)
        except OSError:
            return None
