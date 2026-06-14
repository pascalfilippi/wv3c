"""Stylized Xbox-style controller widget drawn with QPainter."""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QRadialGradient, QFontMetrics,
)

# Internal coordinate space: 700 x 220
INTERNAL_W = 700
INTERNAL_H = 220

# M button positions in internal coords
M_POSITIONS = {
    1: (202, 20),   # top-left shoulder
    2: (498, 20),   # top-right shoulder
    3: (152, 82),   # left grip side
    4: (548, 82),   # right grip side
    5: (188, 170),  # left grip back
    6: (512, 170),  # right grip back
}

DOT_RADIUS = 8
HOVER_RADIUS = 11


class ControllerView(QWidget):
    """Draws a stylized Xbox controller with M-button labels and click signals."""

    button_clicked = pyqtSignal(int)  # m_num 1-6

    def __init__(self, parent=None):
        super().__init__(parent)
        # Each entry: {"text": str, "type": str}
        # type: "gamepad" | "keyboard" | "default" | "disabled" | "unknown"
        self._labels: dict[int, dict] = {
            i: {"text": "Not Assigned", "type": "default"} for i in range(1, 7)
        }
        self._hovered: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(180)

    def set_label(self, m_num: int, text: str, mapping_type: str = "default"):
        self._labels[m_num] = {"text": text, "type": mapping_type}
        self.update()

    def set_all_labels(self, labels: dict):
        """Accept {m_num: {"text":..., "type":...}} or {m_num: str} for compat."""
        for m_num, info in labels.items():
            if isinstance(info, dict):
                self._labels[m_num] = info
            else:
                self._labels[m_num] = {"text": str(info), "type": "default"}
        self.update()

    @staticmethod
    def _label_color(mapping_type: str) -> QColor:
        if mapping_type == "gamepad":
            return QColor("#00c800")   # green — controller button
        if mapping_type == "keyboard":
            return QColor("#5599ff")   # blue — keyboard key
        return QColor("#555555")       # dim gray — not assigned / unknown

    # ---------- coordinate helpers ----------

    def _scale(self) -> float:
        sw = self.width() / INTERNAL_W
        sh = self.height() / INTERNAL_H
        return min(sw, sh)

    def _offset(self) -> tuple[float, float]:
        s = self._scale()
        ox = (self.width() - INTERNAL_W * s) / 2
        oy = (self.height() - INTERNAL_H * s) / 2
        return ox, oy

    def _to_widget(self, ix: float, iy: float) -> tuple[float, float]:
        s = self._scale()
        ox, oy = self._offset()
        return ix * s + ox, iy * s + oy

    def _from_widget(self, wx: float, wy: float) -> tuple[float, float]:
        s = self._scale()
        ox, oy = self._offset()
        return (wx - ox) / s, (wy - oy) / s

    def _hit_button(self, ix: float, iy: float) -> int | None:
        for m_num, (bx, by) in M_POSITIONS.items():
            dist2 = (ix - bx) ** 2 + (iy - by) ** 2
            if dist2 <= (HOVER_RADIUS + 4) ** 2:
                return m_num
        return None

    # ---------- events ----------

    def mouseMoveEvent(self, event):
        ix, iy = self._from_widget(event.position().x(), event.position().y())
        hit = self._hit_button(ix, iy)
        if hit != self._hovered:
            self._hovered = hit
            self.setCursor(Qt.CursorShape.PointingHandCursor if hit else Qt.CursorShape.ArrowCursor)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            ix, iy = self._from_widget(event.position().x(), event.position().y())
            hit = self._hit_button(ix, iy)
            if hit is not None:
                self.button_clicked.emit(hit)

    def leaveEvent(self, event):
        self._hovered = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    # ---------- painting ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._scale()
        ox, oy = self._offset()
        painter.translate(ox, oy)
        painter.scale(s, s)

        self._draw_controller(painter)
        self._draw_labels(painter)
        self._draw_m_buttons(painter)

    def _draw_controller(self, p: QPainter):
        body_color = QColor("#2a2a2a")
        bumper_color = QColor("#353535")
        accent_dark = QColor("#1e1e1e")

        pen_none = QPen(Qt.PenStyle.NoPen)
        p.setPen(pen_none)

        # Left grip
        p.setBrush(QBrush(body_color))
        p.drawRoundedRect(QRectF(162, 105, 90, 88), 16, 16)

        # Right grip
        p.drawRoundedRect(QRectF(448, 105, 90, 88), 16, 16)

        # Main body
        p.drawRoundedRect(QRectF(175, 30, 350, 120), 22, 22)

        # Left bumper
        p.setBrush(QBrush(bumper_color))
        p.drawRoundedRect(QRectF(193, 24, 68, 20), 7, 7)

        # Right bumper
        p.drawRoundedRect(QRectF(439, 24, 68, 20), 7, 7)

        # Left stick
        p.setBrush(QBrush(QColor("#404040")))
        p.drawEllipse(QPointF(248, 88), 22, 22)
        p.setBrush(QBrush(QColor("#505050")))
        p.drawEllipse(QPointF(248, 88), 14, 14)

        # D-pad cross
        p.setBrush(QBrush(QColor("#3a3a3a")))
        p.drawRect(QRectF(206, 107, 14, 42))
        p.drawRect(QRectF(192, 121, 42, 14))

        # Right stick
        p.setBrush(QBrush(QColor("#404040")))
        p.drawEllipse(QPointF(415, 128), 22, 22)
        p.setBrush(QBrush(QColor("#505050")))
        p.drawEllipse(QPointF(415, 128), 14, 14)

        # Face buttons — ABXY
        face_buttons = [
            (QPointF(490, 88), QColor("#993333")),   # B (right)
            (QPointF(472, 106), QColor("#338844")),  # A (bottom)
            (QPointF(454, 88), QColor("#334499")),   # X (left)
            (QPointF(472, 70), QColor("#888822")),   # Y (top)
        ]
        for center, color in face_buttons:
            p.setBrush(QBrush(color))
            p.drawEllipse(center, 10, 10)

        # Xbox button
        p.setBrush(QBrush(QColor("#00a000")))
        p.drawEllipse(QPointF(350, 78), 11, 11)

        # View / Menu buttons
        p.setBrush(QBrush(QColor("#383838")))
        p.drawEllipse(QPointF(315, 78), 7, 7)
        p.drawEllipse(QPointF(385, 78), 7, 7)

    def _draw_m_buttons(self, p: QPainter):
        for m_num, (bx, by) in M_POSITIONS.items():
            is_hovered = (m_num == self._hovered)
            r = HOVER_RADIUS if is_hovered else DOT_RADIUS
            center = QPointF(bx, by)

            if is_hovered:
                # Glow effect
                grad = QRadialGradient(center, r * 2)
                grad.setColorAt(0, QColor(0, 200, 0, 120))
                grad.setColorAt(1, QColor(0, 200, 0, 0))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(grad))
                p.drawEllipse(center, r * 2, r * 2)

            # Green circle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#00c800") if not is_hovered else QColor("#00e000")))
            p.drawEllipse(center, r, r)

            # White number
            font = QFont("Arial", 6 if not is_hovered else 7, QFont.Weight.Bold)
            p.setFont(font)
            p.setPen(QPen(QColor("white")))
            fm = QFontMetrics(font)
            text = str(m_num)
            tw = fm.horizontalAdvance(text)
            th = fm.ascent()
            p.drawText(QPointF(bx - tw / 2, by + th / 2 - 1), text)

    def _draw_labels(self, p: QPainter):
        line_color = QColor("#505050")
        font = QFont("Arial", 8)
        font.setBold(False)
        p.setFont(font)

        left_buttons  = [1, 3, 5]   # line goes left  to x=128
        right_buttons = [2, 4, 6]   # line goes right to x=572

        for m_num in left_buttons:
            bx, by = M_POSITIONS[m_num]
            info = self._labels.get(m_num, {"text": "", "type": "default"})
            text = info["text"]
            color = self._label_color(info["type"])

            # Connecting line
            p.setPen(QPen(line_color, 1))
            p.drawLine(QPointF(bx - DOT_RADIUS - 1, by), QPointF(130, by))

            # Label text
            p.setPen(QPen(color))
            p.drawText(
                QRectF(0, by - 10, 124, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

        for m_num in right_buttons:
            bx, by = M_POSITIONS[m_num]
            info = self._labels.get(m_num, {"text": "", "type": "default"})
            text = info["text"]
            color = self._label_color(info["type"])

            # Connecting line
            p.setPen(QPen(line_color, 1))
            p.drawLine(QPointF(bx + DOT_RADIUS + 1, by), QPointF(570, by))

            # Label text
            p.setPen(QPen(color))
            p.drawText(
                QRectF(576, by - 10, 124, 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )
