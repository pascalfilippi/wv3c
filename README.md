# wolverine-linux

Linux userspace driver for the **Razer Wolverine V3 Pro for Xbox** (VID:PID `1532:0a4c`).

The kernel `xpad` driver handles standard gamepad input (buttons, sticks, triggers, D-pad, extra M1-M6 buttons) out of the box. This project gives you control over the advanced features that require vendor-specific HID commands: RGB lighting, per-profile button remapping, trigger configuration, and device status.

## Features

- **RGB control** — set any 24-bit color, choose from the 8-color built-in palette, or turn the LED off
- **Profile readback** — list all 4 profiles, read their names, button mappings, trigger settings, and LED state
- **Device status** — firmware/hardware version, serial number, polling rate, active profile
- **Battery level** — read charge percentage
- **Button remapping** (read) — shows current mapping for M1-M6 buttons per profile

## Requirements

- Linux with `hidraw` support (standard on any modern kernel)
- Python ≥ 3.10
- Read/write access to `/dev/hidrawN` — either run as root or add a udev rule (see below)

## Installation

```bash
# Clone the repository
git clone https://github.com/pascal-filippi/wolverine-linux.git
cd wolverine-linux

# Create a virtual environment
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Usage

All commands are available through the `wolverine` CLI.

### Device status

```bash
wolverine status          # firmware, hardware, serial, polling rate, active profile
wolverine battery         # battery charge percentage
```

### RGB / LED

```bash
wolverine rgb set red              # named colors: red, green, blue, cyan, magenta,
wolverine rgb set "#ff8800"        #   yellow, orange, purple, pink, white
wolverine rgb set ff8800           # hex without #
wolverine rgb off                  # turn LED off
wolverine rgb palette 0            # built-in palette: 0=green 1=cyan 2=blue 3=purple
                                   #   4=red 5=orange 6=yellow 7=white
wolverine rgb status               # show current LED effect and color
wolverine rgb status -p 2          # show LED state for profile 2
```

### Profiles

```bash
wolverine profile list             # list all 4 profiles, mark active one
wolverine profile show             # full details for the active profile
wolverine profile show 2           # full details for profile 2
```

Profile details include: LED state, button mappings (M1-M6), trigger configuration (mode, actuation range, HyperTrigger), thumbstick deadzones, and D-pad mode.

## Architecture

All device I/O goes through `src/wolverine/device.py:WolverineDevice`. Feature modules call `dev.send_command(cmd_class, cmd_id, data_size, args)`, which wraps the 90-byte Razer HID Feature Report format and issues `HIDIOCSFEATURE`/`HIDIOCGFEATURE` ioctls on `/dev/hidrawN`.

| Module | Purpose |
|--------|---------|
| `src/wolverine/device.py` | Device discovery, report framing, hidraw ioctls |
| `src/wolverine/rgb.py` | LED color and effect commands (class `0x0F`) |
| `src/wolverine/info.py` | Firmware, serial, polling rate, battery (classes `0x00`, `0x07`) |
| `src/wolverine/profile.py` | Profile names, button mappings, trigger/stick config (classes `0x02`, `0x05`, `0x0C`, `0x0F`) |
| `cli/main.py` | Click CLI entrypoint |

See `docs/protocol.md` for a full reference of the HID command classes and message formats.

## Development

```bash
# Install with dev dependencies
.venv/bin/pip install -e ".[dev]"

# Run tests
.venv/bin/pytest
```

One-off probe scripts used during protocol discovery are in `tools/`. These are not part of the library.

## Status

The GET side of all features is implemented and working. SET commands for button remapping exist. SET commands for triggers, polling rate adjustment, and profile management are partially implemented — see `docs/tasks/` for the roadmap.

A PyQt6 GUI is in early development (`wolverine gui`).

## Protocol

The controller uses the standard Razer 90-byte Feature Report format over HID interface 1. Full documentation is in [`docs/protocol.md`](docs/protocol.md).

**Warning**: Never send command class `0x00` / ID `0x04` with mode byte `0x03` — this puts the controller into bootloader mode (VID:PID `1532:110e`) and requires a physical replug to recover.

## License

GPL-3.0-or-later
