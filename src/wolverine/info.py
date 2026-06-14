"""Device information queries."""

from .device import WolverineDevice


def get_firmware_version(dev: WolverineDevice) -> str | None:
    """Read firmware version string."""
    result = dev.send_command(0x00, 0x81, 2, [0x00] * 2)
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    return f"v{d[0]}.{d[1]}" if len(d) >= 2 else None


def get_serial(dev: WolverineDevice) -> str | None:
    """Read device serial/ID. Returns hex string of raw ID bytes."""
    result = dev.send_command(0x00, 0x82, 22, [0x00] * 22)
    if result is None or result[0] != 0x02:
        return None
    d = bytes(result[1]).rstrip(b'\x00')
    if not d:
        return None
    # Check if it's printable ASCII
    if all(0x20 <= b < 0x7F for b in d):
        return d.decode('ascii')
    # Otherwise return as hex
    return d.hex()


def get_hardware_version(dev: WolverineDevice) -> str | None:
    """Read hardware version string."""
    result = dev.send_command(0x00, 0x87, 4, [0x00] * 4)
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    return f"v{d[0]}.{d[1]}.{d[2]}.{d[3]}" if len(d) >= 4 else None


def get_polling_rate(dev: WolverineDevice) -> int | None:
    """Read polling rate in Hz. Derived from interval in 0x00/0x8E byte 1."""
    result = dev.send_command(0x00, 0x8E, 2, [0x00, 0x00])
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    if len(d) < 2 or d[1] == 0:
        return None
    return 1000 // d[1]


def get_device_status(dev: WolverineDevice) -> int | None:
    """Read unknown device status byte (0x00/0xD6). Possibly battery/connection."""
    result = dev.send_command(0x00, 0xD6, 1, [0x00])
    if result is None or result[0] != 0x02:
        return None
    return result[1][0] if len(result[1]) >= 1 else None


def set_polling_rate(dev: WolverineDevice, hz: int) -> bool:
    """Set polling rate. hz must be 250 or 1000."""
    interval = 1000 // hz
    result = dev.send_command(0x00, 0x0E, 2, [0x00, interval])
    return result is not None and result[0] == 0x02


def get_battery(dev: WolverineDevice) -> int | None:
    """Read battery charge level. Returns 0-100 (percent), or None on failure."""
    result = dev.send_command(0x07, 0x80, 2, [0x00, 0x00])
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    if len(d) < 2:
        return None
    return round(d[1] / 255 * 100)
