"""Dark Razer-inspired style sheet for the Wolverine GUI."""

STYLE = """
QWidget { background:#1a1a1a; color:#e8e8e8; font-family:Arial,sans-serif; font-size:13px; }
QMainWindow { background:#1a1a1a; }

/* Cards */
QFrame#card { background:#252525; border-radius:8px; }

/* Tab bar */
QTabBar::tab { background:transparent; color:#888; padding:8px 18px; font-size:12px; font-weight:bold; letter-spacing:1px; border:none; }
QTabBar::tab:selected { color:#00c800; border-bottom:2px solid #00c800; }
QTabBar::tab:hover { color:#cccccc; }
QTabWidget::pane { border:none; }

/* Buttons */
QPushButton { background:#333; border:none; border-radius:4px; padding:7px 18px; color:#ddd; font-size:12px; }
QPushButton:hover { background:#444; }
QPushButton:pressed { background:#222; }
QPushButton#accentBtn { background:#00c800; color:#000; font-weight:bold; }
QPushButton#accentBtn:hover { background:#00e000; }
QPushButton#pollBtn { background:#2a2a2a; border:1px solid #444; border-radius:4px; padding:7px 20px; color:#aaa; font-size:13px; }
QPushButton#pollBtn:checked { background:#00c800; color:#000; border-color:#00c800; font-weight:bold; }

/* Slider */
QSlider::groove:horizontal { background:#333; height:4px; border-radius:2px; }
QSlider::handle:horizontal { background:#888; width:16px; height:16px; margin:-6px 0; border-radius:8px; }
QSlider::sub-page:horizontal { background:#4a4a4a; border-radius:2px; }

/* ComboBox */
QComboBox { background:#2a2a2a; border:1px solid #444; border-radius:4px; padding:5px 10px; color:#e0e0e0; font-size:13px; min-width:130px; }
QComboBox::drop-down { border:none; width:20px; }
QComboBox QAbstractItemView { background:#2a2a2a; border:1px solid #555; selection-background-color:#333; color:#e0e0e0; }

/* Labels */
QLabel#sectionTitle { color:#00c800; font-size:11px; font-weight:bold; letter-spacing:2px; }
QLabel#hint { color:#666; font-size:11px; }
QLabel#batteryLabel { color:#00c800; font-size:13px; font-weight:bold; }
QLabel#windowTitle { color:#e8e8e8; font-size:14px; font-weight:bold; letter-spacing:2px; }

/* Toggle (checkable QPushButton used as toggle) */
QPushButton#toggle { background:#333; border:1px solid #555; border-radius:10px; padding:3px 8px; min-width:42px; min-height:20px; }
QPushButton#toggle:checked { background:#00c800; border-color:#00c800; }

/* RadioButton */
QRadioButton { spacing:8px; color:#ddd; }
QRadioButton::indicator { width:16px; height:16px; border-radius:8px; border:2px solid #555; background:#2a2a2a; }
QRadioButton::indicator:checked { border-color:#00c800; background:#00c800; }

/* Color swatch button */
QPushButton#swatch { border-radius:6px; min-width:36px; max-width:36px; min-height:36px; max-height:36px; border:2px solid transparent; padding:0; }
QPushButton#swatch:checked { border-color:#00c800; }
QPushButton#swatch:hover { border-color:#666; }

/* Dialog */
QDialog { background:#1e1e1e; }
QDialog QLabel { color:#ccc; }

/* Separator in controller page */
QFrame[frameShape="4"] { color:#333; }
"""
