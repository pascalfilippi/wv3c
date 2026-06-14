"""CLI entry point for wolverine-linux."""

import sys

import click

from src.wolverine.device import WolverineDevice
from src.wolverine.rgb import (
    parse_color, set_color, set_off, select_palette,
)
from src.wolverine.info import (
    get_firmware_version, get_serial, get_hardware_version,
    get_polling_rate, get_device_status, get_battery,
)
from src.wolverine.profile import (
    get_active_profile, get_profile_name, get_full_profile, get_led_state,
)


def _open_device() -> WolverineDevice:
    try:
        dev = WolverineDevice()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    return dev


@click.group()
def cli():
    """Control Razer Wolverine V3 Pro advanced features on Linux."""


# --- Device status ---

@cli.command()
def status():
    """Show device info: firmware, serial, polling rate, active profile."""
    with _open_device() as dev:
        fw = get_firmware_version(dev)
        hw = get_hardware_version(dev)
        serial = get_serial(dev)
        poll = get_polling_rate(dev)
        dev_status = get_device_status(dev)
        active = get_active_profile(dev)
        active_name = get_profile_name(dev, active) if active else None

    click.echo(f"Firmware:       {fw or 'unknown'}")
    click.echo(f"Hardware:       {hw or 'unknown'}")
    click.echo(f"Serial:         {serial or 'unknown'}")
    click.echo(f"Polling rate:   {poll or '?'} Hz")
    click.echo(f"Device status:  0x{dev_status:02x}" if dev_status is not None else "Device status:  unknown")
    if active:
        click.echo(f"Active profile: {active} ({active_name})")
    else:
        click.echo("Active profile: unknown")


# --- Battery ---

@cli.command()
def battery():
    """Show battery charge level."""
    with _open_device() as dev:
        level = get_battery(dev)

    if level is None:
        click.echo("Failed to read battery level", err=True)
        sys.exit(1)

    click.echo(f"Battery: {level}%")


# --- Profile commands ---

@cli.group()
def profile():
    """Profile information."""


@profile.command(name="list")
def profile_list():
    """List all profiles and highlight the active one."""
    with _open_device() as dev:
        active = get_active_profile(dev)
        for p in range(1, 5):
            name = get_profile_name(dev, p)
            marker = " *" if p == active else ""
            click.echo(f"  {p}: {name}{marker}")


@profile.command(name="show")
@click.argument("number", type=click.IntRange(1, 4), required=False)
def profile_show(number: int | None):
    """Show full details for a profile (default: active profile)."""
    with _open_device() as dev:
        if number is None:
            number = get_active_profile(dev)
            if number is None:
                click.echo("Could not determine active profile", err=True)
                sys.exit(1)

        p = get_full_profile(dev, number)

    active_marker = ""
    with _open_device() as dev:
        active = get_active_profile(dev)
        if number == active:
            active_marker = " (active)"

    click.echo(f"Profile {p['number']}: {p['name']}{active_marker}")

    # LED
    led = p["led"]
    if led:
        brightness = p["brightness"]
        bright_pct = f"{brightness * 100 // 255}%" if brightness is not None else "?"
        click.echo(f"\n  LED: {led['effect_name']} (brightness {bright_pct})")
        for i, (r, g, b) in enumerate(led["colors"]):
            click.echo(f"    Color {i}: #{r:02x}{g:02x}{b:02x}")

    # Buttons
    if p["buttons"]:
        click.echo(f"\n  Buttons:")
        for btn in p["buttons"]:
            btype = btn["type"]
            if btype == "disabled":
                detail = "disabled"
            elif btype == "default":
                detail = "default"
            elif btype == "gamepad":
                detail = f"gamepad → {btn['button_name']}"
            elif btype == "keyboard":
                mods = btn.get("modifier_names", [])
                key = f"0x{btn['keycode']:02x}"
                if mods:
                    detail = f"keyboard → {'+'.join(mods)}+{key}"
                else:
                    detail = f"keyboard → {key}"
            else:
                detail = f"unknown ({btn.get('raw', '?')})"
            click.echo(f"    {btn['name']:3s}: {detail}")

    # Triggers
    click.echo(f"\n  Triggers:")
    for name, tc in p["triggers"].items():
        if tc is None:
            click.echo(f"    {name}: read error")
            continue
        enabled = tc.get("enabled", False)
        mode = tc.get("mode", 0)
        act_min = tc.get("actuation_min", 0)
        act_max = tc.get("actuation_max", 100)
        ht = "HyperTrigger ON" if enabled else "normal"
        click.echo(f"    {name}: {ht}, actuation {act_min}-{act_max}%, mode {mode}")

    # Sticks
    click.echo(f"\n  Thumbstick deadzones:")
    for name, dz in p["sticks"].items():
        click.echo(f"    {name}: {dz}" if dz is not None else f"    {name}: unknown")

    # D-pad
    if p.get("dpad_mode"):
        click.echo(f"\n  D-pad: {p['dpad_mode']}")


# --- RGB commands ---

@cli.group()
def rgb():
    """LED / RGB lighting control."""


@rgb.command(name="set")
@click.argument("color")
def rgb_set(color: str):
    """Set the LED to a solid color.

    COLOR can be a name (red, green, blue, cyan, magenta, yellow,
    orange, purple, pink, white) or a hex code (ff0000, #00ff00).
    """
    try:
        r, g, b = parse_color(color)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    with _open_device() as dev:
        ok = set_color(dev, r, g, b)

    if ok:
        click.echo(f"LED set to #{r:02x}{g:02x}{b:02x}")
    else:
        click.echo("Failed to set LED color", err=True)
        sys.exit(1)


@rgb.command()
def off():
    """Turn the LED off."""
    with _open_device() as dev:
        ok = set_off(dev)

    if ok:
        click.echo("LED turned off")
    else:
        click.echo("Failed to turn off LED", err=True)
        sys.exit(1)


@rgb.command()
@click.argument("index", type=click.IntRange(0, 7))
def palette(index: int):
    """Select a color from the built-in palette (0-7).

    0=green, 1=cyan, 2=blue, 3=purple, 4=red, 5=orange, 6=yellow, 7=white
    """
    with _open_device() as dev:
        ok = select_palette(dev, index)

    colors = ["green", "cyan", "blue", "purple", "red", "orange", "yellow", "white"]
    if ok:
        click.echo(f"LED set to palette {index} ({colors[index]})")
    else:
        click.echo("Failed to select palette color", err=True)
        sys.exit(1)


@rgb.command(name="status")
@click.option("--profile", "-p", type=click.IntRange(1, 4), default=None,
              help="Profile to read (default: active profile).")
def rgb_status(profile: int | None):
    """Read the current LED state for a profile."""
    with _open_device() as dev:
        if profile is None:
            profile = get_active_profile(dev) or 1
        info = get_led_state(dev, profile)

    if info is None:
        click.echo("Failed to read LED state", err=True)
        sys.exit(1)

    click.echo(f"Profile {profile}: effect={info['effect_name']}")
    for i, (r, g, b) in enumerate(info["colors"]):
        click.echo(f"  Color {i}: #{r:02x}{g:02x}{b:02x}")


@cli.command()
def gui():
    """Launch the graphical controller configurator."""
    from src.wolverine.gui.app import main
    main()


def gui_main():
    """Standalone GUI entry point (used by the flatpak launcher)."""
    from src.wolverine.gui.app import main
    main()


if __name__ == "__main__":
    cli()
