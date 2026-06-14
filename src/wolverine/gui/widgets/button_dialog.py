"""Dialog for configuring an M-button mapping."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QStackedWidget, QWidget, QPushButton,
    QDialogButtonBox, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent

# Ordered gamepad buttons for the dropdown
GAMEPAD_BUTTONS_ORDERED = [
    ("A",      0x20), ("B",     0x21), ("X",    0x22), ("Y",    0x23),
    ("LB",     0x26), ("RB",    0x27), ("LT",   0x24), ("RT",   0x25),
    ("LS (Left Stick Click)",  0x28),
    ("RS (Right Stick Click)", 0x29),
    ("D-Pad Up",    0x2C), ("D-Pad Down",  0x2D),
    ("D-Pad Left",  0x2E), ("D-Pad Right", 0x2F),
    ("Menu",   0x34), ("View",  0x35),
    # 0x37, 0x38, 0x3A are focus-aim buttons — labels TBD, hidden until implemented
]

from PyQt6.QtCore import Qt as _Qt

QT_TO_HID = {
    _Qt.Key.Key_A: 0x04, _Qt.Key.Key_B: 0x05, _Qt.Key.Key_C: 0x06,
    _Qt.Key.Key_D: 0x07, _Qt.Key.Key_E: 0x08, _Qt.Key.Key_F: 0x09,
    _Qt.Key.Key_G: 0x0a, _Qt.Key.Key_H: 0x0b, _Qt.Key.Key_I: 0x0c,
    _Qt.Key.Key_J: 0x0d, _Qt.Key.Key_K: 0x0e, _Qt.Key.Key_L: 0x0f,
    _Qt.Key.Key_M: 0x10, _Qt.Key.Key_N: 0x11, _Qt.Key.Key_O: 0x12,
    _Qt.Key.Key_P: 0x13, _Qt.Key.Key_Q: 0x14, _Qt.Key.Key_R: 0x15,
    _Qt.Key.Key_S: 0x16, _Qt.Key.Key_T: 0x17, _Qt.Key.Key_U: 0x18,
    _Qt.Key.Key_V: 0x19, _Qt.Key.Key_W: 0x1a, _Qt.Key.Key_X: 0x1b,
    _Qt.Key.Key_Y: 0x1c, _Qt.Key.Key_Z: 0x1d,
    _Qt.Key.Key_1: 0x1e, _Qt.Key.Key_2: 0x1f, _Qt.Key.Key_3: 0x20,
    _Qt.Key.Key_4: 0x21, _Qt.Key.Key_5: 0x22, _Qt.Key.Key_6: 0x23,
    _Qt.Key.Key_7: 0x24, _Qt.Key.Key_8: 0x25, _Qt.Key.Key_9: 0x26,
    _Qt.Key.Key_0: 0x27,
    _Qt.Key.Key_Return: 0x28, _Qt.Key.Key_Enter: 0x28,
    _Qt.Key.Key_Escape: 0x29, _Qt.Key.Key_Backspace: 0x2a,
    _Qt.Key.Key_Tab: 0x2b, _Qt.Key.Key_Space: 0x2c,
    _Qt.Key.Key_Minus: 0x2d, _Qt.Key.Key_Equal: 0x2e,
    _Qt.Key.Key_BracketLeft: 0x2f, _Qt.Key.Key_BracketRight: 0x30,
    _Qt.Key.Key_Backslash: 0x31, _Qt.Key.Key_Semicolon: 0x33,
    _Qt.Key.Key_Apostrophe: 0x34, _Qt.Key.Key_QuoteLeft: 0x35,
    _Qt.Key.Key_Comma: 0x36, _Qt.Key.Key_Period: 0x37,
    _Qt.Key.Key_Slash: 0x38, _Qt.Key.Key_CapsLock: 0x39,
    _Qt.Key.Key_F1: 0x3a, _Qt.Key.Key_F2: 0x3b, _Qt.Key.Key_F3: 0x3c,
    _Qt.Key.Key_F4: 0x3d, _Qt.Key.Key_F5: 0x3e, _Qt.Key.Key_F6: 0x3f,
    _Qt.Key.Key_F7: 0x40, _Qt.Key.Key_F8: 0x41, _Qt.Key.Key_F9: 0x42,
    _Qt.Key.Key_F10: 0x43, _Qt.Key.Key_F11: 0x44, _Qt.Key.Key_F12: 0x45,
    _Qt.Key.Key_Right: 0x4f, _Qt.Key.Key_Left: 0x50,
    _Qt.Key.Key_Down: 0x51, _Qt.Key.Key_Up: 0x52,
    # Modifier keys as standalone HID keycodes (0xe0-0xe7)
    _Qt.Key.Key_Control: 0xe0, _Qt.Key.Key_Shift: 0xe1,
    _Qt.Key.Key_Alt: 0xe2, _Qt.Key.Key_Meta: 0xe3,
}

MODIFIER_KEYS = {
    _Qt.Key.Key_Control, _Qt.Key.Key_Shift,
    _Qt.Key.Key_Alt, _Qt.Key.Key_Meta,
}

_MOD_DISPLAY = {
    _Qt.Key.Key_Control: "Ctrl",
    _Qt.Key.Key_Shift:   "Shift",
    _Qt.Key.Key_Alt:     "Alt",
    _Qt.Key.Key_Meta:    "Meta",
}

_MOD_ORDER = [
    _Qt.Key.Key_Control,
    _Qt.Key.Key_Shift,
    _Qt.Key.Key_Alt,
    _Qt.Key.Key_Meta,
]


def qt_mods_to_hid(qt_mods) -> int:
    m = 0
    if qt_mods & _Qt.KeyboardModifier.ControlModifier: m |= 0x01
    if qt_mods & _Qt.KeyboardModifier.ShiftModifier:   m |= 0x02
    if qt_mods & _Qt.KeyboardModifier.AltModifier:     m |= 0x04
    if qt_mods & _Qt.KeyboardModifier.MetaModifier:    m |= 0x08
    return m


_HID_NAMES = {
    0x04: "A", 0x05: "B", 0x06: "C", 0x07: "D", 0x08: "E",
    0x09: "F", 0x0a: "G", 0x0b: "H", 0x0c: "I", 0x0d: "J",
    0x0e: "K", 0x0f: "L", 0x10: "M", 0x11: "N", 0x12: "O",
    0x13: "P", 0x14: "Q", 0x15: "R", 0x16: "S", 0x17: "T",
    0x18: "U", 0x19: "V", 0x1a: "W", 0x1b: "X", 0x1c: "Y",
    0x1d: "Z", 0x1e: "1", 0x1f: "2", 0x20: "3", 0x21: "4",
    0x22: "5", 0x23: "6", 0x24: "7", 0x25: "8", 0x26: "9",
    0x27: "0", 0x28: "Enter", 0x29: "Esc", 0x2a: "Backspace",
    0x2b: "Tab", 0x2c: "Space", 0x2d: "-", 0x2e: "=",
    0x2f: "[", 0x30: "]", 0x31: "\\", 0x33: ";", 0x34: "'",
    0x35: "`", 0x36: ",", 0x37: ".", 0x38: "/", 0x39: "CapsLock",
    0x3a: "F1", 0x3b: "F2", 0x3c: "F3", 0x3d: "F4",
    0x3e: "F5", 0x3f: "F6", 0x40: "F7", 0x41: "F8",
    0x42: "F9", 0x43: "F10", 0x44: "F11", 0x45: "F12",
    0x4f: "Right", 0x50: "Left", 0x51: "Down", 0x52: "Up",
    0xe0: "LCtrl", 0xe1: "LShift", 0xe2: "LAlt", 0xe3: "LMeta",
    0xe4: "RCtrl", 0xe5: "RShift", 0xe6: "RAlt", 0xe7: "RMeta",
}


def _describe_capture(mod_mask: int, hid_code: int) -> str:
    if hid_code in (0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7):
        return _HID_NAMES.get(hid_code, f"0x{hid_code:02x}")
    key_name = _HID_NAMES.get(hid_code, f"0x{hid_code:02x}")
    mod_names = []
    if mod_mask & 0x01: mod_names.append("Ctrl")
    if mod_mask & 0x02: mod_names.append("Shift")
    if mod_mask & 0x04: mod_names.append("Alt")
    if mod_mask & 0x08: mod_names.append("Meta")
    if mod_names:
        return "+".join(mod_names) + "+" + key_name
    return key_name


class KeyCaptureWidget(QLabel):
    """Click to activate, then press a key (with optional modifiers).

    Behaviour:
    - Press a regular key (alone or while holding modifiers) → captures immediately.
    - Press a modifier key and release it without pressing any other key → captures
      the modifier as a standalone key (e.g. LShift, LAlt).
    - While modifiers are held the display shows "Shift + …" as a hint.
    """

    key_captured = pyqtSignal(int, int)  # modifier_mask, hid_keycode

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._held_mods: set = set()   # Qt.Key values currently held
        self._mod_mask = 0
        self._hid_code = 0
        self._has_capture = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(44)
        self.setMinimumWidth(240)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._apply_style(False)
        self._refresh_text()

    # ------------------------------------------------------------------
    # Public API

    def get_capture(self) -> tuple[int, int] | None:
        return (self._mod_mask, self._hid_code) if self._has_capture else None

    def set_from_mapping(self, mapping: dict):
        if mapping.get("type") == "keyboard":
            self._mod_mask = mapping.get("modifier", 0)
            self._hid_code = mapping.get("keycode", 0)
            self._has_capture = True
            self._active = False
            self._apply_style(False)
            self._refresh_text()

    # ------------------------------------------------------------------
    # Internals

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(
                "QLabel { background:#1a2a1a; border:2px solid #00c800; "
                "border-radius:6px; color:#00c800; padding:6px; font-size:13px; }"
            )
        else:
            self.setStyleSheet(
                "QLabel { background:#2a2a2a; border:2px solid #444; "
                "border-radius:6px; color:#ccc; padding:6px; font-size:13px; }"
            )

    def _refresh_text(self):
        if self._active:
            if self._held_mods:
                names = [_MOD_DISPLAY[k] for k in _MOD_ORDER if k in self._held_mods]
                self.setText(" + ".join(names) + " + …")
            else:
                self.setText("Press a key…")
        elif self._has_capture:
            self.setText(_describe_capture(self._mod_mask, self._hid_code))
        else:
            self.setText("Click here, then press a key")

    def _do_capture(self, mod_mask: int, hid_code: int):
        self._mod_mask = mod_mask
        self._hid_code = hid_code
        self._has_capture = True
        self._active = False
        self._held_mods.clear()
        self._apply_style(False)
        self._refresh_text()
        self.key_captured.emit(mod_mask, hid_code)

    # ------------------------------------------------------------------
    # Events

    def mousePressEvent(self, event):
        if event.button() == _Qt.MouseButton.LeftButton:
            self._active = True
            self._held_mods.clear()
            self._apply_style(True)
            self._refresh_text()
            self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._active:
            super().keyPressEvent(event)
            return
        key = _Qt.Key(event.key())
        if key in MODIFIER_KEYS:
            # Accumulate held modifiers — don't capture yet
            self._held_mods.add(key)
            self._refresh_text()
            event.accept()
            return
        # Regular key — capture immediately with whatever modifiers are held
        hid = QT_TO_HID.get(key, 0)
        if hid:
            mod_mask = qt_mods_to_hid(event.modifiers())
            self._do_capture(mod_mask, hid)
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent):
        if not self._active:
            super().keyReleaseEvent(event)
            return
        key = _Qt.Key(event.key())
        if key in MODIFIER_KEYS and key in self._held_mods:
            self._held_mods.discard(key)
            if not self._held_mods:
                # All modifiers released without a regular key → standalone modifier
                hid = QT_TO_HID.get(key, 0)
                if hid:
                    self._do_capture(0, hid)
            else:
                self._refresh_text()
        event.accept()

    def focusOutEvent(self, event):
        if self._active:
            self._active = False
            self._held_mods.clear()
            self._apply_style(False)
            self._refresh_text()
        super().focusOutEvent(event)


class ButtonMappingDialog(QDialog):
    """Modal dialog to configure one M-button's mapping.

    Three options:
      0 — Not Assigned  (sends passthrough bytes 00 10 05 …)
      1 — Controller Button  (gamepad button via dropdown)
      2 — Keyboard Key  (key capture widget)
    """

    def __init__(self, m_num: int, current_mapping: dict, parent=None):
        super().__init__(parent)
        self._m_num = m_num
        self._current = current_mapping
        self._result_data: dict | None = None
        self._selected_gamepad_code: int | None = None
        self._key_capture: KeyCaptureWidget | None = None
        self._gamepad_combo: QComboBox | None = None

        self.setWindowTitle(f"Configure M{m_num}")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._build_ui()
        self._populate_from_mapping(current_mapping)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"Configure M{self._m_num}")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#e8e8e8;")
        layout.addWidget(title)

        # --- Radio buttons (3 options) ---
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(20)
        self._radio_unassigned = QRadioButton("Not Assigned")
        self._radio_gamepad    = QRadioButton("Controller Button")
        self._radio_keyboard   = QRadioButton("Keyboard Key")

        self._radio_group = QButtonGroup(self)
        self._radio_group.addButton(self._radio_unassigned, 0)
        self._radio_group.addButton(self._radio_gamepad,    1)
        self._radio_group.addButton(self._radio_keyboard,   2)

        for r in (self._radio_unassigned, self._radio_gamepad, self._radio_keyboard):
            radio_layout.addWidget(r)
        radio_layout.addStretch()
        layout.addLayout(radio_layout)

        # --- Stacked content area ---
        self._stack = QStackedWidget()
        self._stack.setMinimumHeight(120)

        # Page 0: Not Assigned
        page_unassigned = QWidget()
        pu = QVBoxLayout(page_unassigned)
        pu.addWidget(QLabel("Button will have no effect."))
        pu.addStretch()
        self._stack.addWidget(page_unassigned)

        # Page 1: Controller Button — dropdown
        page_gamepad = QWidget()
        pg = QVBoxLayout(page_gamepad)
        pg.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Select a controller button:")
        hint.setObjectName("hint")
        pg.addWidget(hint)

        self._gamepad_combo = QComboBox()
        self._gamepad_combo.setMinimumWidth(220)
        for name, code in GAMEPAD_BUTTONS_ORDERED:
            self._gamepad_combo.addItem(name, code)
        self._gamepad_combo.currentIndexChanged.connect(self._on_combo_changed)
        pg.addWidget(self._gamepad_combo)
        pg.addStretch()
        self._stack.addWidget(page_gamepad)

        # Page 2: Keyboard Key — capture widget
        page_keyboard = QWidget()
        pk = QVBoxLayout(page_keyboard)
        pk.setContentsMargins(0, 0, 0, 0)
        pk_hint = QLabel(
            "Click the box below, then press the desired key.\n"
            "Hold a modifier (Shift, Ctrl, Alt) before pressing to create a combination.\n"
            "Press a modifier alone and release it to assign just that modifier key."
        )
        pk_hint.setObjectName("hint")
        pk_hint.setWordWrap(True)
        pk.addWidget(pk_hint)

        self._key_capture = KeyCaptureWidget()
        self._key_capture.key_captured.connect(lambda *_: self._update_ok())
        pk.addWidget(self._key_capture)
        pk.addStretch()
        self._stack.addWidget(page_keyboard)

        layout.addWidget(self._stack)

        # --- OK / Cancel ---
        self._btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = self._btn_box.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setObjectName("accentBtn")
        self._btn_box.accepted.connect(self._on_accept)
        self._btn_box.rejected.connect(self.reject)
        layout.addWidget(self._btn_box)

        # Connect radios
        for r in (self._radio_unassigned, self._radio_gamepad, self._radio_keyboard):
            r.toggled.connect(self._on_radio_changed)

        self._on_radio_changed()  # set initial stack page + OK state

    # ------------------------------------------------------------------

    def _on_radio_changed(self):
        idx = self._radio_group.checkedId()
        if idx >= 0:
            self._stack.setCurrentIndex(idx)
        # When switching to controller tab, sync selected code from combo
        if idx == 1:
            self._selected_gamepad_code = self._gamepad_combo.currentData()
        self._update_ok()

    def _on_combo_changed(self, _index: int):
        self._selected_gamepad_code = self._gamepad_combo.currentData()
        self._update_ok()

    def _update_ok(self):
        idx = self._radio_group.checkedId()
        if idx == 0:
            self._ok_btn.setEnabled(True)
        elif idx == 1:
            self._ok_btn.setEnabled(self._selected_gamepad_code is not None)
        elif idx == 2:
            self._ok_btn.setEnabled(
                self._key_capture is not None and
                self._key_capture.get_capture() is not None
            )
        else:
            self._ok_btn.setEnabled(False)

    def _populate_from_mapping(self, mapping: dict):
        t = mapping.get("type", "unknown")
        if t in ("disabled", "default", "unknown"):
            self._radio_unassigned.setChecked(True)
        elif t == "gamepad":
            self._radio_gamepad.setChecked(True)
            code = mapping.get("button_code", 0)
            for i in range(self._gamepad_combo.count()):
                if self._gamepad_combo.itemData(i) == code:
                    self._gamepad_combo.setCurrentIndex(i)
                    break
            self._selected_gamepad_code = code
        elif t == "keyboard":
            self._radio_keyboard.setChecked(True)
            if self._key_capture:
                self._key_capture.set_from_mapping(mapping)
        else:
            self._radio_unassigned.setChecked(True)

    # ------------------------------------------------------------------

    def _on_accept(self):
        idx = self._radio_group.checkedId()
        if idx == 0:
            self._result_data = {
                "type": "default",
                "mapping_8bytes": b'\x00\x10\x05\x00\x00\x00\x00\x00',
            }
        elif idx == 1:
            code = self._selected_gamepad_code
            if code is None:
                return
            self._result_data = {
                "type": "gamepad",
                "mapping_8bytes": bytes([0x00, 0x10, 0x01, code, 0x00, 0x00, 0x00, 0x00]),
            }
        elif idx == 2:
            cap = self._key_capture.get_capture() if self._key_capture else None
            if cap is None:
                return
            mod_mask, hid_code = cap
            self._result_data = {
                "type": "keyboard",
                "mapping_8bytes": bytes([0x00, 0x02, 0x02, mod_mask, hid_code, 0x00, 0x00, 0x00]),
            }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result_data
