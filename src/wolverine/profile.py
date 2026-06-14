"""Profile management and per-profile configuration readback."""

from .device import WolverineDevice

# Button ID to name mapping
BUTTON_NAMES = {
    0x10: "M1",
    0x11: "M2",
    0x12: "M3",
    0x13: "M4",
    0x14: "M5",
    0x15: "M6",
}

# HID modifier bit masks
HID_MODIFIERS = {
    0x01: "LCtrl",
    0x02: "LShift",
    0x04: "LAlt",
    0x08: "LMeta",
    0x10: "RCtrl",
    0x20: "RShift",
    0x40: "RAlt",
    0x80: "RMeta",
}

# Xbox/gamepad button codes (type 10 01) — from USB capture analysis
# UI assignment order: face → d-pad → bumpers+triggers → sticks → menu/view → extra
# Confirmed: 0x23=Y.  Others inferred from sequence & grouping; verify if in doubt.
GAMEPAD_BUTTONS = {
    # Face buttons
    0x20: "A",
    0x21: "B",
    0x22: "X",
    0x23: "Y",        # confirmed
    # Bumpers / digital triggers (UI order: LB, RB, LT, RT)
    0x24: "LT",
    0x25: "RT",
    0x26: "LB",
    0x27: "RB",
    # Thumbstick clicks
    0x28: "LS",
    0x29: "RS",
    # D-pad
    0x2C: "DUp",
    0x2D: "DDown",
    0x2E: "DLeft",
    0x2F: "DRight",
    # Special buttons
    0x34: "Menu",
    0x35: "View",
    # 0x37, 0x38, 0x3A: focus-aim buttons — labels TBD, hidden until implemented
}

TRIGGER_NAMES = {1: "LT", 2: "RT"}
STICK_NAMES = {1: "Left", 2: "Right"}
DPAD_MODES = {0x00: "8-way", 0x01: "4-way"}


def get_active_profile(dev: WolverineDevice) -> int | None:
    """Return the active profile number (1-4), or None on failure."""
    result = dev.send_command(0x05, 0x84, 2, [0x00, 0x00])
    if result is None or result[0] != 0x02:
        return None
    return result[1][0] if len(result[1]) >= 1 else None


def get_profile_name(dev: WolverineDevice, profile: int) -> str | None:
    """Read profile name (UTF-16LE). Profile is 1-4."""
    args = [profile] + [0x00] * 68
    result = dev.send_command(0x05, 0x88, 69, args)
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    if len(d) < 5:
        return None
    str_len = d[4]
    if str_len == 0 or len(d) < 5 + str_len:
        return f"Profile {profile}"
    try:
        return bytes(d[5:5 + str_len]).decode('utf-16-le').rstrip('\x00')
    except (UnicodeDecodeError, ValueError):
        return f"Profile {profile}"


def get_led_state(dev: WolverineDevice, profile: int) -> dict | None:
    """Read the active LED colour for a profile.

    Windows Razer Synapse uses data_size=0x05 with args=[profile, 0x00, 0x0d, 0x00, 0x01].
    The device responds with:
      6 bytes  — num_colors=0: no custom RGB stored (factory default / palette mode)
      9 bytes  — num_colors=1: custom RGB at d[6:9]
    Using data_size=0x1E returns the shared 8-colour palette (same for all profiles).
    """
    args = [profile, 0x00, 0x0d, 0x00, 0x01]
    result = dev.send_command(0x0F, 0x82, 5, args)
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    if len(d) < 6:
        return None
    effect_names = {0x02: "off", 0x03: "spectrum", 0x04: "wave",
                    0x08: "breathing", 0x0B: "reactive", 0x0D: "static"}
    eid = d[2]
    num_colors = d[5]
    info = {
        "effect_id": eid,
        "effect_name": effect_names.get(eid, f"0x{eid:02x}"),
        "num_colors": num_colors,
        "colors": [],
    }
    if num_colors >= 1 and len(d) >= 9:
        info["colors"].append((d[6], d[7], d[8]))
    return info


def set_active_profile(dev: WolverineDevice, profile: int) -> bool:
    """Switch the controller to a different active profile (1-4)."""
    result = dev.send_command(0x05, 0x04, 1, [profile])
    return result is not None and result[0] == 0x02


def get_brightness(dev: WolverineDevice, profile: int) -> int | None:
    """Read LED brightness for a profile (0-255)."""
    args = [profile, 0x00, 0x00]
    result = dev.send_command(0x0F, 0x84, 3, args)
    if result is None or result[0] != 0x02:
        return None
    d = result[1]
    return d[2] if len(d) >= 3 else None


def _decode_modifiers(mod_byte: int) -> list[str]:
    """Decode HID modifier bitmask into modifier names."""
    mods = []
    for bit, name in HID_MODIFIERS.items():
        if mod_byte & bit:
            mods.append(name)
    return mods


def decode_button_mapping(d: bytes) -> dict:
    """Decode the 8 mapping bytes (after profile and button_id).

    Format:
      [0x00, type_hi, type_lo, ...data...]

    Known types:
      00 00 = cleared/disabled
      10 01 = gamepad button remap: byte 3 = button code
      10 05 = default (no remap, passthrough)
      02 02 = keyboard key: byte 3 = modifier mask, byte 4 = HID keycode
    """
    mapping = bytes(d[:8])
    if mapping == b'\x00' * 8:
        return {"type": "disabled"}

    type_hi = mapping[1]
    type_lo = mapping[2]

    if type_hi == 0x10 and type_lo == 0x05:
        return {"type": "default"}

    if type_hi == 0x10 and type_lo == 0x01:
        btn_code = mapping[3]
        # btn_code 0x00 is the device's "cleared/not assigned" sentinel
        if btn_code == 0x00:
            return {"type": "default"}
        return {
            "type": "gamepad",
            "button_code": btn_code,
            "button_name": GAMEPAD_BUTTONS.get(btn_code, f"0x{btn_code:02x}"),
        }

    if type_hi == 0x02 and type_lo == 0x02:
        modifier = mapping[3]
        keycode = mapping[4]
        return {
            "type": "keyboard",
            "modifier": modifier,
            "modifier_names": _decode_modifiers(modifier),
            "keycode": keycode,
        }

    return {"type": "unknown", "raw": mapping.hex(' ')}


def get_button_mappings(dev: WolverineDevice, profile: int) -> list[dict]:
    """Read all 6 button mappings for a profile."""
    buttons = []
    for btn_id in range(0x10, 0x16):
        args = [profile, btn_id] + [0x00] * 8
        result = dev.send_command(0x02, 0x8C, 10, args)
        if result is None or result[0] != 0x02:
            continue
        d = result[1]
        if len(d) < 10:
            continue
        mapping = decode_button_mapping(d[2:10])
        mapping["id"] = btn_id
        mapping["name"] = BUTTON_NAMES.get(btn_id, f"0x{btn_id:02x}")
        mapping["raw"] = bytes(d[2:10]).hex(' ')
        buttons.append(mapping)
    return buttons


def get_trigger_config(dev: WolverineDevice, profile: int,
                       trigger: int) -> dict | None:
    """Read trigger config (trigger=1 for LT, 2 for RT)."""
    info = {"trigger": trigger, "name": TRIGGER_NAMES.get(trigger, f"{trigger}")}

    # Trigger type
    result = dev.send_command(0x0C, 0x96, 4, [profile, trigger, 0x00, 0x00])
    if result and result[0] == 0x02 and len(result[1]) >= 3:
        info["type"] = result[1][2]

    # Enable state
    result = dev.send_command(0x0C, 0x95, 3, [profile, trigger, 0x00])
    if result and result[0] == 0x02 and len(result[1]) >= 3:
        info["enabled"] = bool(result[1][2])

    # Actuation range
    result = dev.send_command(0x0C, 0x93, 4, [profile, trigger, 0x00, 0x00])
    if result and result[0] == 0x02 and len(result[1]) >= 4:
        info["actuation_min"] = result[1][2]
        info["actuation_max"] = result[1][3]

    # Mode
    result = dev.send_command(0x0C, 0x92, 3, [profile, trigger, 0x00])
    if result and result[0] == 0x02 and len(result[1]) >= 3:
        info["mode"] = result[1][2]

    return info


def get_stick_deadzone(dev: WolverineDevice, profile: int,
                       stick: int) -> int | None:
    """Read thumbstick deadzone (stick=1 for left, 2 for right)."""
    result = dev.send_command(0x0C, 0x82, 3, [profile, stick, 0x00])
    if result and result[0] == 0x02 and len(result[1]) >= 3:
        return result[1][2]
    return None


def get_dpad_mode(dev: WolverineDevice, profile: int) -> str | None:
    """Read D-pad mode for a profile. Returns '4-way' or '8-way'."""
    result = dev.send_command(0x0C, 0x97, 2, [profile, 0x00])
    if result and result[0] == 0x02 and len(result[1]) >= 2:
        return DPAD_MODES.get(result[1][1], f"unknown (0x{result[1][1]:02x})")
    return None


def set_button_mapping(dev: WolverineDevice, profile: int, button_id: int,
                       mapping_8bytes: bytes) -> bool:
    """Set 8-byte mapping for one button. mapping_8bytes layout:
    disabled:  b'\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'
    default:   b'\\x00\\x10\\x05\\x00\\x00\\x00\\x00\\x00'
    gamepad:   b'\\x00\\x10\\x01' + bytes([btn_code]) + b'\\x00\\x00\\x00\\x00'
    keyboard:  b'\\x00\\x02\\x02' + bytes([mod_mask, keycode]) + b'\\x00\\x00\\x00'
    """
    args = [profile, button_id] + list(mapping_8bytes[:8])
    result = dev.send_command(0x02, 0x0C, 10, args)
    return result is not None and result[0] == 0x02


def set_brightness(dev: WolverineDevice, profile: int, brightness: int) -> bool:
    """Set LED brightness for a profile. brightness 0-255."""
    result = dev.send_command(0x0F, 0x04, 3, [profile, 0x00, brightness])
    return result is not None and result[0] == 0x02


def mapping_label(mapping: dict) -> str:
    """Human-readable label for a decoded mapping dict."""
    t = mapping.get("type", "unknown")
    if t in ("disabled", "default"):
        return "Not Assigned"
    if t == "gamepad":
        name = mapping.get("button_name", f"0x{mapping.get('button_code', 0):02x}")
        return name
    if t == "keyboard":
        mods = mapping.get("modifier_names", [])
        kc = mapping.get("keycode", 0)
        # modifier key used as a key (0xe0-0xe7)
        MOD_KEYS = {
            0xe0: "LCtrl", 0xe1: "LShift", 0xe2: "LAlt", 0xe3: "LMeta",
            0xe4: "RCtrl", 0xe5: "RShift", 0xe6: "RAlt", 0xe7: "RMeta",
        }
        HID_NAMES = {
            0x04: "A", 0x05: "B", 0x06: "C", 0x07: "D", 0x08: "E", 0x09: "F",
            0x0a: "G", 0x0b: "H", 0x0c: "I", 0x0d: "J", 0x0e: "K", 0x0f: "L",
            0x10: "M", 0x11: "N", 0x12: "O", 0x13: "P", 0x14: "Q", 0x15: "R",
            0x16: "S", 0x17: "T", 0x18: "U", 0x19: "V", 0x1a: "W", 0x1b: "X",
            0x1c: "Y", 0x1d: "Z", 0x1e: "1", 0x1f: "2", 0x20: "3", 0x21: "4",
            0x22: "5", 0x23: "6", 0x24: "7", 0x25: "8", 0x26: "9", 0x27: "0",
            0x28: "Enter", 0x29: "Esc", 0x2a: "Backspace", 0x2b: "Tab",
            0x2c: "Space", 0x2d: "-", 0x2e: "=", 0x2f: "[", 0x30: "]",
            0x33: ";", 0x34: "'", 0x35: "`", 0x36: ",", 0x37: ".", 0x38: "/",
            0x39: "CapsLock", 0x3a: "F1", 0x3b: "F2", 0x3c: "F3", 0x3d: "F4",
            0x3e: "F5", 0x3f: "F6", 0x40: "F7", 0x41: "F8", 0x42: "F9",
            0x43: "F10", 0x44: "F11", 0x45: "F12",
            0x4f: "→", 0x50: "←", 0x51: "↓", 0x52: "↑",
        }
        if kc in MOD_KEYS:
            return MOD_KEYS[kc]
        key = HID_NAMES.get(kc, f"0x{kc:02x}")
        if mods:
            return "+".join(mods) + "+" + key
        return key
    return "Unknown"


def get_full_profile(dev: WolverineDevice, profile: int) -> dict:
    """Read all configuration for a profile."""
    return {
        "number": profile,
        "name": get_profile_name(dev, profile),
        "led": get_led_state(dev, profile),
        "brightness": get_brightness(dev, profile),
        "buttons": get_button_mappings(dev, profile),
        "triggers": {
            "LT": get_trigger_config(dev, profile, 1),
            "RT": get_trigger_config(dev, profile, 2),
        },
        "sticks": {
            "Left": get_stick_deadzone(dev, profile, 1),
            "Right": get_stick_deadzone(dev, profile, 2),
        },
        "dpad_mode": get_dpad_mode(dev, profile),
    }
