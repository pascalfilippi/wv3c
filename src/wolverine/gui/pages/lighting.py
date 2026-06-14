"""Lighting page: brightness and RGB effects."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QRadioButton, QButtonGroup, QColorDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from ...rgb import DEFAULT_PALETTE
from ..utils import run_task as _run_task


def _slider_style(color_hex: str) -> str:
    return (
        f"QSlider::groove:horizontal {{ background:#333; height:4px; border-radius:2px; }}"
        f"QSlider::handle:horizontal {{ background:{color_hex}; width:16px; height:16px; margin:-6px 0; border-radius:8px; }}"
        f"QSlider::sub-page:horizontal {{ background:{color_hex}; border-radius:2px; }}"
    )

_SLIDER_NEUTRAL = _slider_style("#555")


class BrightnessSlider(QWidget):
    """Slider with a floating value bubble that reflects the current LED color."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)

        self._bubble = QLabel("100", self)
        self._bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bubble.setFixedSize(38, 22)
        self._bubble.setStyleSheet(
            "background:#555; color:#ddd; border-radius:4px; "
            "font-size:11px; font-weight:bold;"
        )

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(100)
        self._slider.setStyleSheet(_SLIDER_NEUTRAL)
        self._slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._slider)
        minmax = QHBoxLayout()
        lbl_0 = QLabel("0")
        lbl_0.setObjectName("hint")
        lbl_100 = QLabel("100")
        lbl_100.setObjectName("hint")
        minmax.addWidget(lbl_0)
        minmax.addStretch()
        minmax.addWidget(lbl_100)
        layout.addLayout(minmax)

    @property
    def slider(self) -> QSlider:
        return self._slider

    def set_track_color(self, r: int, g: int, b: int):
        """Update the slider track and bubble to reflect the given LED color."""
        col = f"#{r:02x}{g:02x}{b:02x}"
        lum = (r * 299 + g * 587 + b * 114) // 1000
        text = "#000" if lum > 128 else "#ddd"
        self._slider.setStyleSheet(_slider_style(col))
        self._bubble.setStyleSheet(
            f"background:{col}; color:{text}; border-radius:4px; "
            "font-size:11px; font-weight:bold;"
        )

    def reset_track_color(self):
        """Reset to neutral (for spectrum / off effects)."""
        self._slider.setStyleSheet(_SLIDER_NEUTRAL)
        self._bubble.setStyleSheet(
            "background:#555; color:#ddd; border-radius:4px; "
            "font-size:11px; font-weight:bold;"
        )

    def _on_value_changed(self, value: int):
        self._bubble.setText(str(value))
        self._update_bubble_pos()

    def _update_bubble_pos(self):
        s = self._slider
        if s.maximum() == s.minimum():
            ratio = 0.0
        else:
            ratio = (s.value() - s.minimum()) / (s.maximum() - s.minimum())

        handle_w = 16
        track_w = s.width() - handle_w
        x = int(ratio * track_w) + handle_w // 2 - self._bubble.width() // 2
        slider_top = self._slider.geometry().top()
        y = slider_top - self._bubble.height() - 2
        self._bubble.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_bubble_pos()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_bubble_pos()

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, v: int):
        self._slider.setValue(v)

    def setEnabled(self, enabled: bool):
        self._slider.setEnabled(enabled)
        self._bubble.setVisible(enabled)


class LightingPage(QWidget):
    """Page with brightness and lighting effects controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_profile = 1
        self._current_color: tuple[int, int, int] | None = None
        self._custom_color: tuple[int, int, int] | None = None
        self._custom_swatch: QPushButton | None = None
        self._swatch_buttons: list[QPushButton] = []
        self._swatch_group = QButtonGroup()
        self._swatch_group.setExclusive(True)
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._send_brightness)
        self._pending_brightness: int | None = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Left: Brightness card
        bright_card = QFrame()
        bright_card.setObjectName("card")
        bright_layout = QVBoxLayout(bright_card)
        bright_layout.setContentsMargins(16, 14, 16, 14)
        bright_layout.setSpacing(10)

        header_row = QHBoxLayout()
        bright_title = QLabel("BRIGHTNESS")
        bright_title.setObjectName("sectionTitle")
        header_row.addWidget(bright_title)
        header_row.addSpacing(10)

        self._bright_toggle = QPushButton()
        self._bright_toggle.setObjectName("toggle")
        self._bright_toggle.setCheckable(True)
        self._bright_toggle.setChecked(True)
        self._bright_toggle.setFixedSize(44, 24)
        self._bright_toggle.clicked.connect(self._on_toggle_changed)
        header_row.addWidget(self._bright_toggle)
        header_row.addStretch()
        bright_layout.addLayout(header_row)

        self._brightness_slider_widget = BrightnessSlider()
        self._brightness_slider_widget.slider.valueChanged.connect(
            self._on_brightness_changed
        )
        bright_layout.addWidget(self._brightness_slider_widget)
        bright_layout.addStretch()

        self._bright_status = QLabel("")
        self._bright_status.setObjectName("hint")
        bright_layout.addWidget(self._bright_status)

        main_layout.addWidget(bright_card, 2)

        # Right: Effects card
        effects_card = QFrame()
        effects_card.setObjectName("card")
        effects_layout = QVBoxLayout(effects_card)
        effects_layout.setContentsMargins(16, 14, 16, 14)
        effects_layout.setSpacing(10)

        effects_title = QLabel("EFFECTS")
        effects_title.setObjectName("sectionTitle")
        effects_layout.addWidget(effects_title)

        self._radio_static = QRadioButton("Static")
        self._radio_spectrum = QRadioButton("Spectrum Cycling")
        self._radio_none = QRadioButton("None")
        self._radio_static.setChecked(True)

        self._effect_group = QButtonGroup(self)
        self._effect_group.addButton(self._radio_static, 0)
        self._effect_group.addButton(self._radio_spectrum, 1)
        self._effect_group.addButton(self._radio_none, 2)

        self._radio_static.toggled.connect(self._on_effect_changed)
        self._radio_spectrum.toggled.connect(self._on_effect_changed)
        self._radio_none.toggled.connect(self._on_effect_changed)

        effects_layout.addWidget(self._radio_static)
        effects_layout.addWidget(self._radio_spectrum)
        effects_layout.addWidget(self._radio_none)

        # Color section (only visible for Static)
        self._color_widget = QWidget()
        color_layout = QVBoxLayout(self._color_widget)
        color_layout.setContentsMargins(0, 4, 0, 0)
        color_layout.setSpacing(8)

        color_label = QLabel("Color")
        color_label.setStyleSheet("color:#aaa; font-size:12px;")
        color_layout.addWidget(color_label)

        swatches_layout = QHBoxLayout()
        swatches_layout.setSpacing(6)

        for i, (r, g, b) in enumerate(DEFAULT_PALETTE):
            btn = QPushButton()
            btn.setObjectName("swatch")
            btn.setCheckable(True)
            color_hex = f"#{r:02x}{g:02x}{b:02x}"
            btn.setStyleSheet(
                f"QPushButton#swatch {{ background:{color_hex}; "
                f"border-radius:6px; min-width:36px; max-width:36px; "
                f"min-height:36px; max-height:36px; border:2px solid transparent; padding:0; }}"
                f"QPushButton#swatch:checked {{ border-color:#00c800; }}"
                f"QPushButton#swatch:hover {{ border-color:#888; }}"
            )
            btn.clicked.connect(lambda checked, idx=i, rgb=(r, g, b): self._on_swatch_clicked(idx, rgb))
            self._swatch_group.addButton(btn, i)
            self._swatch_buttons.append(btn)
            swatches_layout.addWidget(btn)

        self._plus_btn = QPushButton("+")
        self._plus_btn.setFixedSize(36, 36)
        self._plus_btn.setStyleSheet(
            "QPushButton { background:#2a2a2a; border:2px solid #555; "
            "border-radius:6px; color:#aaa; font-size:18px; "
            "min-width:36px; max-width:36px; min-height:36px; max-height:36px; padding:0; }"
            "QPushButton:hover { background:#383838; border-color:#777; color:#ddd; }"
        )
        self._plus_btn.clicked.connect(self._on_custom_color)
        swatches_layout.addWidget(self._plus_btn)
        swatches_layout.addStretch()

        color_layout.addLayout(swatches_layout)
        effects_layout.addWidget(self._color_widget)

        self._effects_status = QLabel("")
        self._effects_status.setObjectName("hint")
        effects_layout.addWidget(self._effects_status)
        effects_layout.addStretch()

        main_layout.addWidget(effects_card, 3)

        if self._swatch_buttons:
            self._swatch_buttons[0].setChecked(True)

    def load_profile(self, profile_num: int):
        """Load lighting state for this profile in a background thread."""
        self._current_profile = profile_num
        self._bright_status.setText("Loading...")

        def _do_load():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.profile import get_brightness, get_led_state
            with WolverineDevice() as dev:
                brightness = get_brightness(dev, profile_num)
                led_state = get_led_state(dev, profile_num)
            return {"brightness": brightness, "led_state": led_state}

        def _on_done(result):
            brightness = result.get("brightness")
            led_state = result.get("led_state")

            if brightness is not None:
                val = brightness * 100 // 255
                self._brightness_slider_widget.slider.blockSignals(True)
                self._brightness_slider_widget.setValue(val)
                self._brightness_slider_widget.slider.blockSignals(False)
                self._brightness_slider_widget._on_value_changed(val)
                on = (brightness > 0)
                self._bright_toggle.setChecked(on)
                self._brightness_slider_widget.setEnabled(on)

            if led_state:
                eid = led_state.get("effect_id", 0x0D)

                # Block radio signals during load to avoid sending commands
                for rb in (self._radio_static, self._radio_spectrum, self._radio_none):
                    rb.blockSignals(True)

                if eid == 0x0D:  # static
                    self._radio_static.setChecked(True)
                    colors = led_state.get("colors", [])
                    if colors:
                        # Custom RGB was stored — match to palette or show custom swatch
                        r, g, b = colors[0]
                        self._current_color = (r, g, b)
                        self._try_select_palette_color(r, g, b)
                    else:
                        # num_colors=0: no custom RGB (factory default = green palette[0])
                        self._current_color = DEFAULT_PALETTE[0]
                        if self._swatch_buttons:
                            self._swatch_buttons[0].setChecked(True)
                elif eid == 0x03:  # spectrum
                    self._radio_spectrum.setChecked(True)
                    self._current_color = None
                elif eid == 0x02:  # off
                    self._radio_none.setChecked(True)
                    self._current_color = None

                for rb in (self._radio_static, self._radio_spectrum, self._radio_none):
                    rb.blockSignals(False)

            self._update_color_section_visibility()
            self._update_slider_color()
            self._bright_status.setText("")

        def _on_error(err):
            self._bright_status.setText(f"Load error: {err}")

        _run_task(_do_load, _on_done, _on_error)

    def _try_select_palette_color(self, r: int, g: int, b: int):
        """Select the matching palette swatch, or add a custom swatch."""
        for i, (pr, pg, pb) in enumerate(DEFAULT_PALETTE):
            if pr == r and pg == g and pb == b:
                if i < len(self._swatch_buttons):
                    self._swatch_buttons[i].setChecked(True)
                return
        self._set_custom_swatch_color(r, g, b)

    def _set_custom_swatch_color(self, r: int, g: int, b: int):
        """Add or update the custom swatch."""
        self._custom_color = (r, g, b)
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        swatch_css = (
            f"QPushButton#swatch {{ background:{color_hex}; "
            f"border-radius:6px; min-width:36px; max-width:36px; "
            f"min-height:36px; max-height:36px; border:2px solid transparent; padding:0; }}"
            f"QPushButton#swatch:checked {{ border-color:#00c800; }}"
            f"QPushButton#swatch:hover {{ border-color:#888; }}"
        )
        if self._custom_swatch is None:
            btn = QPushButton()
            btn.setObjectName("swatch")
            btn.setCheckable(True)
            custom_id = len(DEFAULT_PALETTE)
            self._swatch_group.addButton(btn, custom_id)
            self._swatch_buttons.append(btn)
            color_vl = self._color_widget.layout()
            for i in range(color_vl.count()):
                item = color_vl.itemAt(i)
                if item and item.layout():
                    hbl = item.layout()
                    idx = hbl.indexOf(self._plus_btn)
                    if idx >= 0:
                        hbl.insertWidget(idx, btn)
                        break
            self._custom_swatch = btn
            btn.clicked.connect(
                lambda checked, rgb=(r, g, b): self._on_swatch_clicked(-1, rgb)
            )
        self._custom_swatch.setStyleSheet(swatch_css)
        self._custom_swatch.setChecked(True)

    def _update_color_section_visibility(self):
        self._color_widget.setVisible(self._radio_static.isChecked())

    def _update_slider_color(self):
        """Sync the brightness slider track and toggle color with the current state."""
        if self._radio_static.isChecked() and self._current_color:
            r, g, b = self._current_color
            col = f"#{r:02x}{g:02x}{b:02x}"
            self._brightness_slider_widget.set_track_color(r, g, b)
            self._bright_toggle.setStyleSheet(
                "QPushButton#toggle { background:#333; border:1px solid #555; "
                "border-radius:10px; padding:3px 8px; min-width:42px; min-height:20px; }"
                f"QPushButton#toggle:checked {{ background:{col}; border-color:{col}; }}"
            )
        else:
            self._brightness_slider_widget.reset_track_color()
            self._bright_toggle.setStyleSheet(
                "QPushButton#toggle { background:#333; border:1px solid #555; "
                "border-radius:10px; padding:3px 8px; min-width:42px; min-height:20px; }"
                "QPushButton#toggle:checked { background:#555; border-color:#888; }"
            )

    # ------------------------------------------------------------------
    # UI event handlers

    def _on_toggle_changed(self):
        on = self._bright_toggle.isChecked()
        self._brightness_slider_widget.setEnabled(on)
        if not on:
            self._pending_brightness = 0
        else:
            self._pending_brightness = self._brightness_slider_widget.value() * 255 // 100
        self._debounce_timer.stop()
        self._send_brightness()

    def _on_brightness_changed(self, value: int):
        if not self._bright_toggle.isChecked():
            return
        self._pending_brightness = value * 255 // 100
        self._debounce_timer.start()

    def _on_effect_changed(self):
        self._update_color_section_visibility()
        if self._radio_spectrum.isChecked():
            self._update_slider_color()
            self._apply_spectrum()
        elif self._radio_none.isChecked():
            self._update_slider_color()
            self._apply_off()
        elif self._radio_static.isChecked():
            # If no color was previously set, default to the first swatch (green)
            if self._current_color is None:
                self._current_color = DEFAULT_PALETTE[0]
                if self._swatch_buttons:
                    self._swatch_buttons[0].setChecked(True)
            self._update_slider_color()
            self._apply_color(*self._current_color)

    def _on_swatch_clicked(self, idx: int, rgb: tuple[int, int, int]):
        if not self._radio_static.isChecked():
            self._radio_static.setChecked(True)
        r, g, b = rgb
        self._current_color = (r, g, b)
        self._update_slider_color()
        self._apply_color(r, g, b)

    def _on_custom_color(self):
        initial = QColor(*self._custom_color) if self._custom_color else QColor("#ffffff")
        color = QColorDialog.getColor(initial, self, "Choose Custom Color")
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            self._current_color = (r, g, b)
            self._set_custom_swatch_color(r, g, b)
            if not self._radio_static.isChecked():
                self._radio_static.setChecked(True)
            self._update_slider_color()
            self._apply_color(r, g, b)

    # ------------------------------------------------------------------
    # Device commands

    def _send_brightness(self):
        if self._pending_brightness is None:
            return
        profile = self._current_profile
        brightness = self._pending_brightness

        def _do_set():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.profile import set_brightness
            with WolverineDevice() as dev:
                return set_brightness(dev, profile, brightness)

        def _on_done(ok):
            self._bright_status.setText("" if ok else "Failed to set brightness.")

        def _on_error(err):
            self._bright_status.setText(f"Error: {err}")

        _run_task(_do_set, _on_done, _on_error)

    def _apply_color(self, r: int, g: int, b: int):
        profile = self._current_profile
        self._effects_status.setText("Applying...")

        def _do_set():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.rgb import set_color
            with WolverineDevice() as dev:
                return set_color(dev, r, g, b, profile=profile)

        def _on_done(ok):
            self._effects_status.setText("" if ok else "Failed to set color.")

        def _on_error(err):
            self._effects_status.setText(f"Error: {err}")

        _run_task(_do_set, _on_done, _on_error)

    def _apply_spectrum(self):
        profile = self._current_profile
        self._effects_status.setText("Applying...")

        def _do_set():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.rgb import set_spectrum
            with WolverineDevice() as dev:
                return set_spectrum(dev, profile=profile)

        def _on_done(ok):
            self._effects_status.setText("" if ok else "Failed to set spectrum.")

        def _on_error(err):
            self._effects_status.setText(f"Error: {err}")

        _run_task(_do_set, _on_done, _on_error)

    def _apply_off(self):
        profile = self._current_profile
        self._effects_status.setText("Applying...")

        def _do_set():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.rgb import set_off
            with WolverineDevice() as dev:
                return set_off(dev, profile=profile)

        def _on_done(ok):
            self._effects_status.setText("" if ok else "Failed to turn off LED.")

        def _on_error(err):
            self._effects_status.setText(f"Error: {err}")

        _run_task(_do_set, _on_done, _on_error)
