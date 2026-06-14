"""RGB LED control for the Wolverine V3 Pro."""

from .device import WolverineDevice

CMD_CLASS = 0x0F
CMD_SET = 0x02
EFFECT_STATIC = 0x0D
EFFECT_OFF = 0x02

# Default spectrum palette
DEFAULT_PALETTE = [
    (0x00, 0xFF, 0x00),  # 0: green
    (0x00, 0xFF, 0xFF),  # 1: cyan
    (0x00, 0x00, 0xFF),  # 2: blue
    (0x80, 0x00, 0x80),  # 3: purple
    (0xFF, 0x00, 0x00),  # 4: red
    (0xFF, 0xA5, 0x00),  # 5: orange
    (0xFF, 0xFF, 0x00),  # 6: yellow
    (0xFF, 0xFF, 0xFF),  # 7: white
]

NAMED_COLORS = {
    "red": (0xFF, 0x00, 0x00),
    "green": (0x00, 0xFF, 0x00),
    "blue": (0x00, 0x00, 0xFF),
    "white": (0xFF, 0xFF, 0xFF),
    "cyan": (0x00, 0xFF, 0xFF),
    "magenta": (0xFF, 0x00, 0xFF),
    "yellow": (0xFF, 0xFF, 0x00),
    "orange": (0xFF, 0xA5, 0x00),
    "purple": (0x80, 0x00, 0x80),
    "pink": (0xFF, 0x69, 0xB4),
}


def parse_color(color_str: str) -> tuple[int, int, int]:
    """Parse a color string (name or hex) into (R, G, B)."""
    color_str = color_str.lower().strip()

    if color_str in NAMED_COLORS:
        return NAMED_COLORS[color_str]

    # Strip leading # if present
    hex_str = color_str.lstrip("#")
    if len(hex_str) == 6:
        try:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b)
        except ValueError:
            pass

    raise ValueError(
        f"Unknown color '{color_str}'. Use a name ({', '.join(NAMED_COLORS)}) "
        f"or hex code (e.g. ff0000, #00ff00)"
    )


def set_color(dev: WolverineDevice, r: int, g: int, b: int,
              profile: int = 0x01) -> bool:
    """Set the LED to a solid RGB color for the given profile."""
    args = [profile, 0x00, EFFECT_STATIC, 0x08, 0x01, 0x01, r, g, b]
    result = dev.send_command(CMD_CLASS, CMD_SET, len(args), args)
    return result is not None and result[0] == 0x02


def set_off(dev: WolverineDevice, profile: int = 0x01) -> bool:
    """Turn the LED off for the given profile."""
    args = [profile, 0x00, EFFECT_OFF, 0x00, 0x01, 0x00]
    result = dev.send_command(CMD_CLASS, CMD_SET, len(args), args)
    return result is not None and result[0] == 0x02


def select_palette(dev: WolverineDevice, index: int,
                   profile: int = 0x01) -> bool:
    """Select a color from the stored palette (0-7) for the given profile."""
    args = [profile, 0x00, EFFECT_STATIC, index, 0x01, 0x00]
    result = dev.send_command(CMD_CLASS, CMD_SET, len(args), args)
    return result is not None and result[0] == 0x02


def set_spectrum(dev: WolverineDevice, profile: int = 0x01) -> bool:
    """Set LED to spectrum cycling effect for the given profile."""
    args = [profile, 0x00, 0x03, 0x00, 0x01, 0x00]
    result = dev.send_command(CMD_CLASS, CMD_SET, len(args), args)
    return result is not None and result[0] == 0x02


