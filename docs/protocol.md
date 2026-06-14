# Razer Wolverine V3 Pro for Xbox - Protocol Documentation

## Device Information

- **VID:PID**: `1532:0a4c` (normal mode), `1532:0a3f` (Xbox mode)
- **Name**: Razer Wolverine V3 Pro for Xbox
- **Firmware**: v2.0 (bcdDevice 1.01)
- **Serial**: 762450C1340496​3
- **USB Speed**: Full Speed (12 Mbps)
- **Physical**: `usb-0000:00:14.0-10`

## USB Interface Layout (Normal Mode - 0x0A4C)

| Interface | Class | Subclass/Protocol | Endpoints | Driver | Purpose |
|-----------|-------|-------------------|-----------|--------|---------|
| 0 | 0xFF (Vendor) | 0x5D/0x01 (Xbox 360) | EP1 IN + EP1 OUT (Interrupt) | xpad | Gamepad input (XInput) |
| 1 | 0x03 (HID) | 0x00/0x01 (Keyboard) | EP2 IN (Interrupt only) | usbhid → hidrawN | HID config channel |
| 2 | 0x01 (Audio Control) | -- | -- | -- | Audio routing |
| 3 | 0x01 (Audio Streaming) | -- | -- | -- | Microphone input |
| 4 | 0x01 (Audio Streaming) | -- | -- | -- | Headphone output |

**Interface 0**: Standard Xbox gamepad (kernel xpad). ALL button/stick/trigger input goes here,
including extra buttons (M1-M4, claw bumpers). No HID reports on Interface 1 when pressing buttons.

**Interface 1**: Configuration only. No OUT endpoint - uses HID Feature Reports (SET_FEATURE/GET_FEATURE
control transfers) via Report ID 0x04.

## HID Report Descriptor (Interface 1, 200 bytes)

| Report ID | Type | Size | Usage Page | Purpose |
|-----------|------|------|------------|---------|
| 0x01 | Input | 63 bytes | Generic Desktop | Unknown (no reports observed) |
| 0x02 | Input | 9 bytes | Keyboard/Keypad | Keyboard emulation (6KRO) |
| 0x03 | Input | 8 bytes | Generic Desktop / Mouse | Mouse emulation (5 btn + axes) |
| 0x04 | **Feature** | **90 bytes** | **Vendor 0xFF00** | **Razer config channel** |
| 0x05 | Input | 21 bytes | Consumer | Media keys |

## Communication Protocol

### Transport

HID Feature Reports via Report ID 0x04. Linux hidraw ioctls:
- Send: `HIDIOCSFEATURE(91)` with `[0x04] + [90-byte Razer report]`
- Read: `HIDIOCGFEATURE(91)` with buffer `[0x04] + [90 bytes]`

### Razer 90-byte Report Format (CONFIRMED WORKING)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | Status | 0x00=New, 0x01=Busy, 0x02=OK, 0x03=Unsupported, 0x05=Wrong Mode |
| 1 | 1 | Transaction ID | Echo'd back. 0x1F default, all TIDs work. |
| 2-3 | 2 | Remaining Packets | 0x0000 |
| 4 | 1 | Protocol Type | 0x00 |
| 5 | 1 | Data Size | Count of valid argument bytes |
| 6 | 1 | Command Class | Feature category |
| 7 | 1 | Command ID | GET commands: 0x80+, SET commands: 0x00-0x0F |
| 8-87 | 80 | Arguments | Zero-padded |
| 88 | 1 | CRC | XOR of bytes 2-87 |
| 89 | 1 | Reserved | 0x00 |

## Discovered Command Classes

### Class 0x00 - Device Information

| GET ID | SET ID | Data | Description |
|--------|--------|------|-------------|
| 0x81 | -- | `02 00` | Firmware version (v2.0) |
| 0x82 | -- | `37 36 32 ...` | Serial number (ASCII) |
| 0x84 | **0x04** | `00 00` | Device mode. **DANGER: SET 0x03 = bootloader mode!** |
| 0x85 | -- | `01 00` | Unknown flag |
| 0x86 | -- | `00 00` | Unknown |
| 0x87 | -- | `02 00 09 00` | Hardware version (v2.0.9.0) |
| 0x88 | -- | `01 00` | Unknown flag |
| 0x8E | **0x0E** | `[profile] [interval]` | **Polling interval** in ms. interval=1→1000Hz, interval=4→250Hz. profile=0 for global. |
| 0xD6 | -- | `00` | Unknown status (0x00 when wired) |

### Class 0x02 - Button Remapping

| GET ID | SET ID | Data | Description |
|--------|--------|------|-------------|
| 0x84 | -- | `06 10 11 12 13 14 15` | Remappable button list: count + 6 button IDs |
| 0x8C | 0x0C | See below | Per-button mapping (per profile) |

**Button IDs**: 0x10=M1, 0x11=M2, 0x12=M3, 0x13=M4, 0x14=M5, 0x15=M6

**Button mapping format** (0x02/0x8C GET, 0x02/0x0C SET):
`[profile, button_id, 0x00, type_hi, type_lo, data...]` (10 bytes total)

| type_hi | type_lo | Meaning | Data format |
|---------|---------|---------|-------------|
| 0x00 | 0x00 | Disabled/cleared | All zeros |
| 0x10 | 0x05 | Default (passthrough) | No extra data |
| 0x10 | 0x01 | Gamepad button remap | byte5 = button code (e.g. 0x23=Y) |
| 0x02 | 0x02 | Keyboard key | byte5 = HID modifier mask, byte6 = HID keycode |

**HID modifier mask** (byte 5 in keyboard type):
0x01=LCtrl, 0x02=LShift, 0x04=LAlt, 0x08=LMeta, 0x10=RCtrl, 0x20=RShift, 0x40=RAlt, 0x80=RMeta

**Gamepad button codes** (used as byte5 in `10 01` mapping type):

| Code | Button | Code | Button | Code | Button |
|------|--------|------|--------|------|--------|
| 0x20 | A | 0x24 | LT¹ | 0x2C | D-pad Up |
| 0x21 | B | 0x25 | RT¹ | 0x2D | D-pad Down |
| 0x22 | X | 0x26 | LB¹ | 0x2E | D-pad Left |
| 0x23 | **Y** ✓ | 0x27 | RB¹ | 0x2F | D-pad Right |
| 0x28 | LS | 0x34 | Menu | 0x37 | Share¹ |
| 0x29 | RS | 0x35 | View | 0x38 | Mute¹ |
|      |    |      |      | 0x3A | Xbox¹  |

✓ = confirmed from USB capture. ¹ = inferred from UI assignment order; names may be wrong.
Source: `docs/captures/allcontrollerbuttonsassignedandsomekezboardkeys.pcapng`
UI order used: face buttons → D-pad → {0x26,0x27,0x24,0x25} → sticks → menu/view → extra.

**Keyboard encoding** (type `0x02/0x02`):

Format: `[0x00, 0x02, 0x02, modifier_mask, keycode, 0x00, 0x00, 0x00]`
- `modifier_mask`: HID bitmask — 0x01=LCtrl, 0x02=LShift, 0x04=LAlt, 0x08=LMeta, 0x10=RCtrl, 0x20=RShift, 0x40=RAlt, 0x80=RMeta
- `keycode`: standard HID USB usage code (0x04='a' … 0x1d='z', 0x1e-0x27='1'-'0', …)
- Standalone modifier key (press Shift by itself): put HID modifier usage in keycode (0xe0=LCtrl, 0xe1=LShift, 0xe2=LAlt, 0xe3=LMeta, 0xe4=RCtrl, 0xe5=RShift, 0xe6=RAlt, 0xe7=RMeta), modifier_mask=0x00

**Confirmed examples**:
- Gamepad Y button: `00 10 01 23 00 00 00 00`
- Keyboard 'c': `00 02 02 00 06 00 00 00`
- Keyboard 'b': `00 02 02 00 05 00 00 00`
- Keyboard 'q': `00 02 02 00 14 00 00 00`
- Standalone LAlt key: `00 02 02 00 e2 00 00 00`
- Standalone LShift key: `00 02 02 00 e1 00 00 00`
- Keyboard Up Arrow: `00 02 02 00 52 00 00 00`
- Keyboard Shift+2 ("): `00 02 02 02 1f 00 00 00`  ← modifier_mask=0x02 for LShift
- Cleared: `00 00 00 00 00 00 00 00`

### Class 0x05 - Buttons / Profiles

| GET ID | SET ID | Data | Description |
|--------|--------|------|-------------|
| 0x80 | -- | `04` | Profile count (4) |
| 0x81 | -- | `04 01 02 03 04` | Profile IDs |
| 0x84 | 0x04 | GET: `[n] 00` / SET: `[n]` | **Active profile number** (1-4, confirmed changes with physical switch) |
| 0x88 | -- | See below | Profile name (UTF-16LE, per profile) |
| 0x8A | -- | `04 00` | Unknown |

**Profile name format** (0x05/0x88): `[profile_num, 0x00, 0x00, 0x00, str_len, UTF-16LE_name...]`
- 69 bytes total, str_len=0x12 (18 bytes = 9 chars)
- Default names: "Profile 1" through "Profile 4"

### Class 0x07 - Sensor Readback

| GET ID | SET ID | Data | Description |
|--------|--------|------|-------------|
| 0x80 | -- | `[0x00, battery_byte]` | **Battery level**: `battery_byte / 255 * 100` = percent |
| 0x83 | 0x03 | `84 03` | Unknown config |
| 0x84 | -- | `00 00`/`00 01` | Unknown flag (polled repeatedly by app) |
| 0x87 | -- | `0e` | Unknown (14) |

Note: The Windows app repeatedly polls 0x07/0x84 + 0x07/0x80 in a loop after init.
0x07/0x80 byte 1 encodes battery level (0x00=0%, 0xFF=100%).

### Class 0x0A - Profile Management

| GET ID | SET ID | Data | Description |
|--------|--------|------|-------------|
| 0x80 | 0x00 | `01 01 03 28 00 00 00 00` | Profile config. Byte 1 = profile number. |
| 0x81 | -- | `00 00` | Unknown |
| -- | 0x02 | (mirrors 0x80 args) | Profile save? (returns Busy sometimes) |
| -- | 0x04 | (mirrors 0x80 args) | Profile apply? (returns OK) |
| -- | 0x05 | (mirrors 0x80 args) | Profile activate? (returns OK) |
| 0x88 | -- | `ff ff` | Unknown |

Note: Physical profile switching (button combo) generates zero USB traffic - handled entirely in firmware.
Profile readback (0x0A/0x80) does NOT reflect hardware profile state.

### Class 0x0C - Trigger & Thumbstick Configuration

Per-profile trigger and thumbstick settings. All commands take `[profile, ...]` as first arg.
Two triggers (1=LT, 2=RT) and two sticks (1=left, 2=right).

| GET ID | SET ID | Args | Description |
|--------|--------|------|-------------|
| 0x82 | 0x02 | `[profile, stick, deadzone]` | Thumbstick deadzone. P1: 0x28=40, P2-4: 0x32=50 |
| 0x85 | 0x05 | `[profile, trigger, 0x00, 0x07, curve...]` | Trigger sensitivity curve (7 points) |
| 0x86 | 0x06 | `[profile, 0x05, value]` | Unknown (0x43=67 for all profiles) |
| 0x92 | 0x12 | `[profile, trigger, mode]` | Trigger mode (0x00=normal) |
| 0x93 | 0x13 | `[profile, trigger, min, max]` | Trigger actuation range (0x00-0x64 = 0-100%) |
| 0x95 | 0x15 | `[profile, trigger, enabled]` | HyperTrigger enable (0x00=off) |
| 0x96 | 0x16 | `[profile, trigger, type, param]` | Trigger type (0x0A=standard) |
| 0x97 | 0x17 | `[profile, mode]` | **D-pad mode**: 0x00=8-way, 0x01=4-way |

### Class 0x0F - LED / Lighting (CONFIRMED WORKING)

| GET ID | SET ID | Data | Description |
|--------|--------|------|-------------|
| 0x80 | -- | `05 19 03 01 02` | LED info. Byte 1=0x19=25 (brightness level). |
| 0x81 | -- | `00 00 0d 02 03 04 08 0b` | Supported effects. IDs: 0x02,0x03,0x04,0x08,0x0b |
| 0x82 | 0x02 | See below | Effect + color data (per storage/profile) |
| 0x84 | 0x04 | `[profile, 0x00, brightness]` | Brightness per zone. brightness=0x00-0xFF |

### Class 0x16 - HyperSense Haptic Descriptor

Chunked JSON + binary transfer describing the trigger haptic capabilities.

| GET ID | Data | Description |
|--------|------|-------------|
| 0x90 | `05 89` | Total descriptor size (0x0589 = 1417 bytes) |
| 0x91 | `[offset_hi, offset_lo, chunk_size, data...]` | Descriptor chunk (77 bytes per chunk) |

**JSON payload** (first ~800 bytes):
```json
{
  "DeviceName": "Sage T1",
  "Manufacturer": "Razer",
  "NumberBodyPart": 2,
  "Bodypart": [
    {
      "BodypartID": 216,
      "Perception": 1,
      "Characteristics": {
        "Resolution": {"AllEqual": 1, "Angle": 1, "Height": 1, "Offset": 0},
        "ValueReport": [{"ActuatorType": 2, "FrequencyMax": 400, "FrequencyMin": 30, "FrequencyResonance": 50}]
      },
      "StreamCharacteristics": {"Bands": 3, "Points": 4, "Transients": 2}
    },
    {"BodypartID": 116, "...": "same as above"}
  ]
}
```

Binary section after JSON contains:
- Profile names (UTF-16LE): "Profile 1" through "Profile 4"
- Sensitivity curve lookup tables (256 entries)
- Haptic frequency response curves

## LED Control Protocol (CONFIRMED WORKING)

The key discovery: the same command `0x0F/0x02` serves both storage and apply functions,
distinguished by the **param2 byte** (offset 4 in args).

### GET LED State (0x0F/0x82)

**Command**: Class `0x0F`, ID `0x82`, Data Size `0x05`

Args: `[profile, 0x00, 0x0D, 0x00, 0x01]`

Response data:
- 6 bytes: `num_colors=0` — factory default / palette mode (no custom RGB stored)
- 9 bytes: `num_colors=1` — custom RGB at d[6:9]

Response layout: `[profile, zone, effect_id, color_index, apply, num_colors, R, G, B]`

Using `data_size=0x1E` returns the shared 8-colour palette (same for all profiles).

### SET LED Color (Store + Apply in one command)

**Command**: Class `0x0F`, ID `0x02`, Data Size `0x09`

| Arg Offset | Field | Description |
|------------|-------|-------------|
| 0 | storage | Profile slot (0x01 for current profile) |
| 1 | zone | LED zone (0x00) |
| 2 | effect_id | Effect type (0x0D for static color) |
| 3 | color_index | Palette index (0x00-0x07 for existing, 0x08+ for new) |
| 4 | apply | **0x01 = apply to hardware, 0x00 = store only** |
| 5 | num_colors | Number of RGB colors following (1 for static) |
| 6-8 | R, G, B | Color value |

**Example - Set LED to red:**
```
Args: [0x01, 0x00, 0x0D, 0x08, 0x01, 0x01, 0xFF, 0x00, 0x00]
         │     │     │     │     │     │     └─ R=255, G=0, B=0
         │     │     │     │     │     └─ 1 color
         │     │     │     │     └─ Apply to hardware
         │     │     │     └─ Palette index 8 (new slot)
         │     │     └─ Effect 0x0D (static color)
         │     └─ Zone 0
         └─ Storage/profile 1
```

### Select Existing Palette Color (No new color data)

**Command**: Class `0x0F`, ID `0x02`, Data Size `0x06`

| Arg Offset | Field | Description |
|------------|-------|-------------|
| 0 | storage | Profile slot |
| 1 | zone | LED zone (0x00) |
| 2 | effect_id | Effect type (0x0D) |
| 3 | color_index | Palette index to display (0x00-0x07) |
| 4 | apply | 0x01 |
| 5 | reserved | 0x00 |

**Default palette (effect 0x0D):**

| Index | Color | RGB |
|-------|-------|-----|
| 0 | Green | 00FF00 |
| 1 | Cyan | 00FFFF |
| 2 | Blue | 0000FF |
| 3 | Purple | 800080 |
| 4 | Red | FF0000 |
| 5 | Orange | FFA500 |
| 6 | Yellow | FFFF00 |
| 7 | White | FFFFFF |

### SET LED Off

**Command**: Class `0x0F`, ID `0x02`, Data Size `0x06`

Args: `[profile, 0x00, 0x02, 0x00, 0x01, 0x00]`

Effect 0x02 turns the LED off when applied.

### Supported Effect IDs

| ID | Effect | Notes |
|----|--------|-------|
| 0x02 | Off | Turns LED off when applied |
| 0x03 | Spectrum cycling | Cycles through colors |
| 0x04 | Wave | Animated wave |
| 0x08 | Breathing | Pulsing effect |
| 0x0B | Reactive | Reacts to button presses |
| 0x0D | Static color | Main effect for solid color display |

## Windows App Initialization Sequence

When the Razer Controller Setup app connects, it performs this sequence:

1. **USB enumeration** - standard device/config descriptors
2. **Device info** - serial (0x00/0x82), unknown flags (0x00/0x86)
3. **HyperSense descriptor** - read full JSON+binary haptic descriptor (0x16/0x90 + 0x91 chunks)
4. **Per-profile loop** (profiles 1-4, each reads):
   - LED capability (0x0F/0x80), brightness (0x0F/0x84)
   - LED palette + current effect (0x0F/0x82 x2)
   - Profile flags (0x00/0x8E)
   - Button mappings (0x02/0x8C x6 buttons)
   - Trigger type, enable, actuation, mode, curve (0x0C/0x96,95,93,92,85 x2 triggers)
   - Trigger general (0x0C/0x97)
   - Thumbstick deadzones (0x0C/0x82 x2)
   - Unknown 0x0C/0x86
5. **Status check** (0x00/0xD6)
6. **Apply current profile settings** - writes back trigger/stick/LED/button config for active profile
7. **Polling loop** - repeatedly reads 0x07/0x84 + 0x07/0x80 (battery level readback)

## Important Notes

- **NEVER send `0x00/0x04` SET with mode `0x03`** - puts controller into bootloader (1532:110e)
- Physical profile switching is firmware-internal (no USB traffic)
- Xbox mode (0x0A3F) uses GIP protocol on IF0, NOT Razer HID Feature Reports
- All commands use Interface 1 (HID, hidrawN)
- Controller can disconnect if commands are sent too rapidly - add 150ms+ delays

## Input Behavior

All gamepad input (buttons, sticks, triggers, D-pad) goes through Interface 0 (xpad).
Interface 1 generates NO input reports when buttons are pressed. The extra buttons
(M1-M4, claw bumpers) are remapped by firmware and sent as standard Xbox inputs on IF0.
