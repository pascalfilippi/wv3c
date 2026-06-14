"""Customize page: button mappings + polling rate."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt

from ..utils import run_task as _run_task
from ..widgets.controller import ControllerView
from ..widgets.button_dialog import ButtonMappingDialog


class CustomizePage(QWidget):
    """Page with controller button mapping and polling rate controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_profile = 1
        self._button_mappings: list[dict] = []
        self._current_poll_hz: int | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setObjectName("hint")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status_label)

        # Controller view
        self._controller = ControllerView()
        self._controller.setMinimumHeight(240)
        self._controller.button_clicked.connect(self._on_button_clicked)
        layout.addWidget(self._controller)

        # Bottom cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        # Polling rate card
        poll_card = QFrame()
        poll_card.setObjectName("card")
        poll_layout = QVBoxLayout(poll_card)
        poll_layout.setContentsMargins(16, 14, 16, 14)
        poll_layout.setSpacing(8)

        poll_title = QLabel("WIRED POLLING RATE")
        poll_title.setObjectName("sectionTitle")
        poll_layout.addWidget(poll_title)

        poll_desc = QLabel("The frequency (Hz) of data updates in a second.")
        poll_desc.setObjectName("hint")
        poll_desc.setWordWrap(True)
        poll_layout.addWidget(poll_desc)

        poll_btns_layout = QHBoxLayout()
        poll_btns_layout.setSpacing(8)

        self._btn_250 = QPushButton("250")
        self._btn_250.setObjectName("pollBtn")
        self._btn_250.setCheckable(True)
        self._btn_250.setFixedWidth(80)
        self._btn_250.clicked.connect(lambda: self._set_polling_rate(250))

        self._btn_1000 = QPushButton("1000")
        self._btn_1000.setObjectName("pollBtn")
        self._btn_1000.setCheckable(True)
        self._btn_1000.setFixedWidth(80)
        self._btn_1000.clicked.connect(lambda: self._set_polling_rate(1000))

        poll_btns_layout.addWidget(self._btn_250)
        poll_btns_layout.addWidget(self._btn_1000)
        poll_btns_layout.addStretch()
        poll_layout.addLayout(poll_btns_layout)

        self._poll_hint_label = QLabel("")
        self._poll_hint_label.setObjectName("hint")
        self._poll_hint_label.setWordWrap(True)
        poll_layout.addWidget(self._poll_hint_label)
        poll_layout.addStretch()

        cards_layout.addWidget(poll_card, 1)

        # Haptic intensity card (disabled)
        haptic_card = QFrame()
        haptic_card.setObjectName("card")
        haptic_layout = QVBoxLayout(haptic_card)
        haptic_layout.setContentsMargins(16, 14, 16, 14)
        haptic_layout.setSpacing(8)

        haptic_title = QLabel("HAPTIC INTENSITY")
        haptic_title.setObjectName("sectionTitle")
        haptic_title.setStyleSheet("color: #555; font-size:11px; font-weight:bold; letter-spacing:2px;")
        haptic_layout.addWidget(haptic_title)

        haptic_body = QLabel("Not yet implemented (protocol unknown)")
        haptic_body.setObjectName("hint")
        haptic_body.setWordWrap(True)
        haptic_layout.addWidget(haptic_body)
        haptic_layout.addStretch()
        haptic_card.setEnabled(False)

        cards_layout.addWidget(haptic_card, 1)
        layout.addLayout(cards_layout)

    def load_profile(self, profile_num: int):
        """Load button mappings and polling rate for a profile in a background thread."""
        self._current_profile = profile_num
        self._status_label.setText("Loading...")

        def _do_load():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.profile import get_button_mappings, mapping_label
            from src.wolverine.info import get_polling_rate

            with WolverineDevice() as dev:
                mappings = get_button_mappings(dev, profile_num)
                poll_hz = get_polling_rate(dev)

            labels = {}
            for m in mappings:
                btn_id = m.get("id", 0)
                m_num = btn_id - 0x10 + 1  # 0x10->1, 0x11->2, etc.
                labels[m_num] = {"text": mapping_label(m), "type": m.get("type", "default")}

            return {"mappings": mappings, "labels": labels, "poll_hz": poll_hz}

        def _on_done(result):
            self._button_mappings = result["mappings"]
            self._controller.set_all_labels(result["labels"])
            poll_hz = result["poll_hz"]
            self._current_poll_hz = poll_hz
            self._update_poll_buttons(poll_hz)
            self._poll_hint_label.setText("")
            self._status_label.setText("")

        def _on_error(err):
            self._status_label.setText(f"Load error: {err}")

        _run_task(_do_load, _on_done, _on_error)

    def _update_poll_buttons(self, hz: int | None):
        self._btn_250.setChecked(hz == 250)
        self._btn_1000.setChecked(hz == 1000)

    def _on_button_clicked(self, m_num: int):
        """Open the mapping dialog for the clicked M-button."""
        # Find current mapping for this button
        btn_id = 0x10 + m_num - 1
        current = {"type": "default"}
        for m in self._button_mappings:
            if m.get("id") == btn_id:
                current = m
                break

        dialog = ButtonMappingDialog(m_num, current, parent=self)
        if dialog.exec() == ButtonMappingDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result is not None:
                self._apply_mapping(m_num, btn_id, result)

    def _apply_mapping(self, m_num: int, btn_id: int, result: dict):
        """Send the new mapping to the device in a background thread."""
        profile = self._current_profile
        mapping_bytes = result["mapping_8bytes"]
        self._status_label.setText("Saving...")

        def _do_set():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.profile import set_button_mapping
            with WolverineDevice() as dev:
                ok = set_button_mapping(dev, profile, btn_id, mapping_bytes)
            return ok

        def _on_done(ok):
            if ok:
                # Refresh label
                self._status_label.setText("")
                # Reload this button's label
                from src.wolverine.profile import decode_button_mapping, mapping_label
                new_mapping = decode_button_mapping(mapping_bytes)
                self._controller.set_label(
                    m_num,
                    mapping_label(new_mapping),
                    new_mapping.get("type", "default"),
                )
                # Update internal state
                for m in self._button_mappings:
                    if m.get("id") == btn_id:
                        m.update(new_mapping)
                        break
            else:
                self._status_label.setText("Failed to save mapping.")

        def _on_error(err):
            self._status_label.setText(f"Error: {err}")

        _run_task(_do_set, _on_done, _on_error)

    def _set_polling_rate(self, hz: int):
        """Set polling rate to 250 or 1000 Hz, then read back to verify."""
        self._update_poll_buttons(hz)
        self._poll_hint_label.setText("")
        self._status_label.setText(f"Setting polling rate to {hz} Hz...")

        def _do_set():
            from src.wolverine.device import WolverineDevice
            from src.wolverine.info import set_polling_rate, get_polling_rate
            with WolverineDevice() as dev:
                set_polling_rate(dev, hz)
                actual_hz = get_polling_rate(dev)
            return actual_hz

        def _on_done(actual_hz):
            self._current_poll_hz = actual_hz
            self._update_poll_buttons(actual_hz)
            self._status_label.setText("")
            if hz == 1000 and actual_hz != 1000:
                self._poll_hint_label.setText(
                    "1000 Hz is only available while connected via USB cable."
                )

        def _on_error(err):
            self._status_label.setText(f"Error: {err}")
            self._update_poll_buttons(self._current_poll_hz)

        _run_task(_do_set, _on_done, _on_error)
