"""Main application window."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QStackedWidget, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from .pages.customize import CustomizePage
from .pages.lighting import LightingPage
from .utils import run_task


class _ProfileListener(QThread):
    """Reads unsolicited IN reports from the controller to detect profile switches.

    The controller sends a 64-byte input report when the user changes profile via
    the hardware button combo (○+A/B/X/Y).  The report is identified by bytes 6-9
    == [0x09, 0x0c, 0xf0, 0x07]; the active profile number (1-4) is at byte 10.
    """
    profile_changed = pyqtSignal(int)

    _SIG = bytes([0x09, 0x0c, 0xf0, 0x07])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        import select
        import os
        from src.wolverine.device import find_device

        path = find_device()
        if not path:
            return
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            return
        try:
            while not self._stop_flag:
                r, _, _ = select.select([fd], [], [], 0.5)
                if not r:
                    continue
                try:
                    data = os.read(fd, 64)
                except OSError:
                    break
                if len(data) >= 11 and data[6:10] == self._SIG:
                    profile = data[10]
                    if 1 <= profile <= 4:
                        self.profile_changed.emit(profile)
        finally:
            os.close(fd)


class MainWindow(QMainWindow):
    """Main application window with header, profile selector, tab bar, and pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_profile = 1
        self._device_found = True
        self._loading = False
        self._reconnect_checking = False
        self._profile_switching = False
        self._profile_listener: _ProfileListener | None = None
        self._build_ui()

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(2000)
        self._reconnect_timer.timeout.connect(self._check_reconnect)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("background:#111111; border-bottom:1px solid #2a2a2a;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        title_label = QLabel("WOLVERINE V3 PRO XBOX")
        title_label.setObjectName("windowTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self._battery_label = QLabel("...")
        self._battery_label.setObjectName("batteryLabel")
        header_layout.addWidget(self._battery_label)

        root_layout.addWidget(header)

        # Profile + tab bar row
        nav_bar = QWidget()
        nav_bar.setFixedHeight(44)
        nav_bar.setStyleSheet("background:#161616; border-bottom:1px solid #222;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(8)

        # Profile selector — show the controller shortcut for each profile
        _profile_shortcuts = ["○ + A", "○ + B", "○ + X", "○ + Y"]
        self._profile_combo = QComboBox()
        for i in range(1, 5):
            self._profile_combo.addItem(f"Profile {i}  ({_profile_shortcuts[i - 1]})", i)
        self._profile_combo.setFixedWidth(140)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        nav_layout.addWidget(self._profile_combo)

        nav_layout.addSpacing(12)

        # Tab buttons
        tab_names = ["CUSTOMIZE", "TRIGGERS", "THUMBSTICKS", "LIGHTING", "POWER", "CALIBRATION"]
        active_tabs = {"CUSTOMIZE", "LIGHTING"}

        self._tab_btns: dict[str, QPushButton] = {}
        for name in tab_names:
            btn = QPushButton(name)
            btn.setFlat(True)
            if name in active_tabs:
                btn.setStyleSheet(
                    "QPushButton { background:transparent; color:#888; padding:8px 14px; "
                    "font-size:12px; font-weight:bold; letter-spacing:1px; border:none; }"
                    "QPushButton:hover { color:#cccccc; }"
                    "QPushButton[active=true] { color:#00c800; border-bottom:2px solid #00c800; }"
                )
                btn.setProperty("active", False)
                btn.clicked.connect(lambda checked, n=name: self._on_tab_clicked(n))
            else:
                btn.setStyleSheet(
                    "QPushButton { background:transparent; color:#444; padding:8px 14px; "
                    "font-size:12px; font-weight:bold; letter-spacing:1px; border:none; }"
                )
                btn.setEnabled(False)
            self._tab_btns[name] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        root_layout.addWidget(nav_bar)

        # Content area
        self._content_stack = QStackedWidget()
        root_layout.addWidget(self._content_stack)

        # Pages
        self._customize_page = CustomizePage()
        self._lighting_page = LightingPage()

        self._content_stack.addWidget(self._customize_page)   # index 0
        self._content_stack.addWidget(self._lighting_page)     # index 1

        # Not-found / wrong-mode page
        self._not_found_page = QWidget()
        nf_layout = QVBoxLayout(self._not_found_page)
        nf_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nf_layout.setSpacing(16)

        self._nf_label = QLabel("")
        self._nf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._nf_label.setStyleSheet("color:#888; font-size:14px;")
        self._nf_label.setWordWrap(True)
        nf_layout.addWidget(self._nf_label)

        retry_btn = QPushButton("Retry Now")
        retry_btn.setFixedWidth(120)
        retry_btn.clicked.connect(self._initial_load)
        nf_layout.addWidget(retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        nf_hint = QLabel("Checking automatically every 2 seconds…")
        nf_hint.setObjectName("hint")
        nf_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nf_layout.addWidget(nf_hint)

        self._content_stack.addWidget(self._not_found_page)  # index 2

        # Set initial active tab
        self._set_active_tab("CUSTOMIZE")

    def _set_active_tab(self, name: str):
        """Visually highlight the active tab and switch the stacked page."""
        for tab_name, btn in self._tab_btns.items():
            if tab_name in ("CUSTOMIZE", "LIGHTING"):
                is_active = (tab_name == name)
                btn.setProperty("active", is_active)
                if is_active:
                    btn.setStyleSheet(
                        "QPushButton { background:transparent; color:#00c800; padding:8px 14px; "
                        "font-size:12px; font-weight:bold; letter-spacing:1px; "
                        "border:none; border-bottom:2px solid #00c800; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background:transparent; color:#888; padding:8px 14px; "
                        "font-size:12px; font-weight:bold; letter-spacing:1px; border:none; }"
                        "QPushButton:hover { color:#cccccc; }"
                    )

        if name == "CUSTOMIZE":
            self._content_stack.setCurrentIndex(0)
        elif name == "LIGHTING":
            self._content_stack.setCurrentIndex(1)

    def _on_tab_clicked(self, name: str):
        self._set_active_tab(name)
        # Load current profile data for the new page
        profile = self._current_profile
        if name == "CUSTOMIZE":
            self._customize_page.load_profile(profile)
        elif name == "LIGHTING":
            self._lighting_page.load_profile(profile)

    def _on_profile_changed(self, index: int):
        profile = self._profile_combo.itemData(index)
        if profile is None:
            return
        self._current_profile = profile

        # Tell the controller to switch profiles; suppress poll until SET completes
        if self._device_found:
            self._profile_switching = True

            def _do_switch():
                from src.wolverine.device import WolverineDevice
                from src.wolverine.profile import set_active_profile
                with WolverineDevice() as dev:
                    set_active_profile(dev, profile)

            def _switch_done(_):
                self._profile_switching = False

            def _switch_err(_):
                self._profile_switching = False

            run_task(_do_switch, _switch_done, _switch_err)

        # Reload active page
        current_idx = self._content_stack.currentIndex()
        if current_idx == 0:
            self._customize_page.load_profile(profile)
        elif current_idx == 1:
            self._lighting_page.load_profile(profile)

    def showEvent(self, event):
        super().showEvent(event)
        self._initial_load()

    def closeEvent(self, event):
        self._stop_reconnect_polling()
        self._stop_profile_listener()
        super().closeEvent(event)


    def _initial_load(self):
        """Detect device mode, then load battery/profile data in background."""
        if self._loading:
            return
        self._loading = True

        def _do_load():
            from src.wolverine.device import check_device_mode, WolverineDevice
            from src.wolverine.info import get_battery
            from src.wolverine.profile import get_active_profile

            mode = check_device_mode()
            if mode != 'pc':
                return {"found": False, "xbox_mode": (mode == 'xbox')}
            with WolverineDevice() as dev:
                battery = get_battery(dev)
                active_profile = get_active_profile(dev)
            return {"found": True, "battery": battery, "active_profile": active_profile}

        def _on_done(result):
            self._loading = False
            if not result.get("found"):
                self._device_found = False
                self._stop_profile_listener()
                self._battery_label.setText("Not connected")
                if result.get("xbox_mode"):
                    self._nf_label.setText(
                        "Controller detected in Xbox mode (1532:0a3f).\n\n"
                        "This program requires PC mode (1532:0a4c).\n\n"
                        "To switch to PC mode, press:  ○ + Menu + A\n\n"
                        "The program will connect automatically once switched."
                    )
                else:
                    self._nf_label.setText(
                        "Controller not found.\n\n"
                        "This program only supports the Razer Wolverine V3 Pro\n"
                        "in PC mode (VID:PID 1532:0a4c).\n\n"
                        "Make sure the device is connected and you have\n"
                        "permission to access /dev/hidrawN.\n\n"
                        "Try: sudo chmod a+rw /dev/hidraw*"
                    )
                self._content_stack.setCurrentIndex(2)
                self._start_reconnect_polling()
                return

            # Device found in PC mode
            self._stop_reconnect_polling()
            self._device_found = True
            battery = result.get("battery")
            self._battery_label.setText(f"Battery: {battery}%" if battery is not None else "")

            active_profile = result.get("active_profile")
            if active_profile and 1 <= active_profile <= 4:
                self._profile_combo.blockSignals(True)
                self._profile_combo.setCurrentIndex(active_profile - 1)
                self._profile_combo.blockSignals(False)
                self._current_profile = active_profile

            # Show customize page and load it
            self._set_active_tab("CUSTOMIZE")
            self._customize_page.load_profile(self._current_profile)
            self._start_profile_listener()

        def _on_error(err):
            self._loading = False
            self._battery_label.setText("Not connected")
            self._nf_label.setText(
                f"Failed to connect: {err}\n\n"
                "This program only supports the Razer Wolverine V3 Pro\n"
                "in PC mode (VID:PID 1532:0a4c).\n\n"
                "Make sure you have permission to access /dev/hidrawN.\n"
                "Try: sudo chmod a+rw /dev/hidraw*"
            )
            self._content_stack.setCurrentIndex(2)
            self._start_reconnect_polling()

        run_task(_do_load, _on_done, _on_error)

    # ------------------------------------------------------------------
    # Profile listener (controller → app sync via IN reports)

    def _start_profile_listener(self):
        self._stop_profile_listener()
        self._profile_listener = _ProfileListener(self)
        self._profile_listener.profile_changed.connect(self._on_controller_profile_changed)
        self._profile_listener.start()

    def _stop_profile_listener(self):
        if self._profile_listener is not None:
            self._profile_listener.stop()
            self._profile_listener.wait(1000)
            self._profile_listener = None

    def _on_controller_profile_changed(self, profile: int):
        """Called when the controller sends a profile-change IN report."""
        if self._profile_switching:
            return
        if profile == self._current_profile:
            return
        self._current_profile = profile
        self._profile_combo.blockSignals(True)
        self._profile_combo.setCurrentIndex(profile - 1)
        self._profile_combo.blockSignals(False)
        current_idx = self._content_stack.currentIndex()
        if current_idx == 0:
            self._customize_page.load_profile(profile)
        elif current_idx == 1:
            self._lighting_page.load_profile(profile)

    # ------------------------------------------------------------------
    # Reconnect polling

    def _start_reconnect_polling(self):
        if not self._reconnect_timer.isActive():
            self._reconnect_timer.start()

    def _stop_reconnect_polling(self):
        self._reconnect_timer.stop()

    def _check_reconnect(self):
        """Periodic background check while on the not-found page."""
        if self._reconnect_checking or self._loading:
            return
        self._reconnect_checking = True

        def _do_check():
            from src.wolverine.device import check_device_mode
            return check_device_mode()

        def _on_result(mode):
            self._reconnect_checking = False
            if mode == 'pc':
                # Device appeared in PC mode — trigger full load
                self._stop_reconnect_polling()
                self._initial_load()
            elif mode == 'xbox' and "Xbox mode" not in self._nf_label.text():
                # Switched from not-found to xbox-mode — update message
                self._nf_label.setText(
                    "Controller detected in Xbox mode (1532:0a3f).\n\n"
                    "This program requires PC mode (1532:0a4c).\n"
                    "Switch the controller to PC mode — refer to your\n"
                    "controller's manual for the button combination.\n\n"
                    "The program will connect automatically once switched."
                )

        def _on_error(_):
            self._reconnect_checking = False

        run_task(_do_check, _on_result, _on_error)
