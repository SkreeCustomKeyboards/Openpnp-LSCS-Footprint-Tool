"""Graphical footprint preview widget.

Renders footprint pads with scale markings and dimensions.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from typing import Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.footprint import Footprint, Pad


class FootprintPreviewWidget(QWidget):
    """Widget that renders a footprint with pads and scale markings.

    Shows footprint centered at origin with:
    - Pads drawn to scale
    - Grid/scale markings in mm
    - Center crosshair
    - Body outline
    - Click on pads to see details

    Signals:
        pad_clicked: Emitted with Pad object when pad is clicked
    """

    pad_clicked = pyqtSignal(object)  # Emits Pad object

    def __init__(self, parent=None):
        super().__init__(parent)
        self._footprint: Optional[Footprint] = None
        self._selected_pad: Optional[Pad] = None
        self._scale = 1.0
        self._center_x = 0.0
        self._center_y = 0.0
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        # Colors
        self._bg_color = QColor("#2b2b2b")
        self._grid_color = QColor("#404040")
        self._center_color = QColor("#808080")
        self._pad_color = QColor("#d4af37")  # Gold color for pads
        self._body_color = QColor("#505050")
        self._text_color = QColor("#cccccc")

    def set_footprint(self, footprint: Optional[Footprint]):
        """Set the footprint to display.

        Args:
            footprint: Footprint object to render, or None to clear
        """
        self._footprint = footprint
        self._selected_pad = None
        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Paint the footprint."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), self._bg_color)

        if not self._footprint:
            # Show placeholder message
            painter.setPen(self._text_color)
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "No footprint loaded")
            return

        # Calculate scaling to fit footprint in widget
        widget_w = self.width()
        widget_h = self.height()

        # Get footprint bounds
        bounds = self._footprint.calculate_bounds()
        min_x, min_y, max_x, max_y = bounds

        # Add margin (20% of size)
        margin_factor = 1.4
        footprint_w = (max_x - min_x) * margin_factor
        footprint_h = (max_y - min_y) * margin_factor

        # Prevent division by zero
        if footprint_w <= 0:
            footprint_w = 10
        if footprint_h <= 0:
            footprint_h = 10

        # Calculate scale (pixels per mm)
        scale_x = widget_w / footprint_w
        scale_y = widget_h / footprint_h
        scale = min(scale_x, scale_y)

        # Center point in widget coordinates
        center_x = widget_w / 2
        center_y = widget_h / 2

        # Store for mouse click handling
        self._scale = scale
        self._center_x = center_x
        self._center_y = center_y

        # Draw grid and scale markings
        self._draw_grid(painter, center_x, center_y, scale, footprint_w, footprint_h)

        # Draw body outline
        self._draw_body(painter, center_x, center_y, scale)

        # Draw center crosshair
        self._draw_center(painter, center_x, center_y, scale)

        # Draw pads
        self._draw_pads(painter, center_x, center_y, scale)

        # Draw dimensions
        self._draw_dimensions(painter, center_x, center_y, scale)

    def _draw_grid(self, painter: QPainter, cx: float, cy: float, scale: float,
                   footprint_w: float, footprint_h: float):
        """Draw grid lines and scale markings.

        Args:
            painter: QPainter object
            cx: Center X in widget coordinates
            cy: Center Y in widget coordinates
            scale: Pixels per mm
            footprint_w: Footprint width in mm
            footprint_h: Footprint height in mm
        """
        painter.setPen(QPen(self._grid_color, 1))

        # Determine grid spacing (1mm, 2mm, 5mm, or 10mm)
        if scale > 50:
            grid_spacing = 1.0
        elif scale > 20:
            grid_spacing = 2.0
        elif scale > 10:
            grid_spacing = 5.0
        else:
            grid_spacing = 10.0

        # Draw vertical grid lines
        num_lines = int(footprint_w / grid_spacing) + 1
        for i in range(-num_lines, num_lines + 1):
            x_mm = i * grid_spacing
            x_px = cx + x_mm * scale
            if 0 <= x_px <= self.width():
                painter.drawLine(QPointF(x_px, 0), QPointF(x_px, self.height()))

        # Draw horizontal grid lines
        num_lines = int(footprint_h / grid_spacing) + 1
        for i in range(-num_lines, num_lines + 1):
            y_mm = i * grid_spacing
            y_px = cy + y_mm * scale
            if 0 <= y_px <= self.height():
                painter.drawLine(QPointF(0, y_px), QPointF(self.width(), y_px))

        # Draw scale markings
        painter.setPen(self._text_color)
        painter.setFont(QFont("Arial", 8))

        # X-axis markings (bottom)
        for i in range(-num_lines, num_lines + 1):
            x_mm = i * grid_spacing
            x_px = cx + x_mm * scale
            if 0 <= x_px <= self.width() and x_mm != 0:
                painter.drawText(QPointF(x_px - 15, self.height() - 5), f"{x_mm:.0f}")

        # Y-axis markings (left)
        for i in range(-num_lines, num_lines + 1):
            y_mm = i * grid_spacing
            y_px = cy + y_mm * scale
            if 0 <= y_px <= self.height() and y_mm != 0:
                painter.drawText(QPointF(5, y_px + 5), f"{y_mm:.0f}")

    def _draw_center(self, painter: QPainter, cx: float, cy: float, scale: float):
        """Draw center crosshair.

        Args:
            painter: QPainter object
            cx: Center X
            cy: Center Y
            scale: Pixels per mm
        """
        painter.setPen(QPen(self._center_color, 1, Qt.PenStyle.DashLine))

        # Crosshair size in mm
        crosshair_size = 2.0 * scale

        # Draw cross
        painter.drawLine(QPointF(cx - crosshair_size, cy), QPointF(cx + crosshair_size, cy))
        painter.drawLine(QPointF(cx, cy - crosshair_size), QPointF(cx, cy + crosshair_size))

    def _draw_body(self, painter: QPainter, cx: float, cy: float, scale: float):
        """Draw component body outline.

        Args:
            painter: QPainter object
            cx: Center X
            cy: Center Y
            scale: Pixels per mm
        """
        if not self._footprint:
            return

        body_w = self._footprint.body_width * scale
        body_h = self._footprint.body_height * scale

        painter.setPen(QPen(self._body_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw rectangle centered at origin
        rect = QRectF(
            cx - body_w / 2,
            cy - body_h / 2,
            body_w,
            body_h
        )
        painter.drawRect(rect)

    def _draw_pads(self, painter: QPainter, cx: float, cy: float, scale: float):
        """Draw all pads.

        Args:
            painter: QPainter object
            cx: Center X
            cy: Center Y
            scale: Pixels per mm
        """
        if not self._footprint:
            return

        for pad in self._footprint.pads:
            # Convert mm to pixels
            x_px = cx + pad.x * scale
            y_px = cy + pad.y * scale
            w_px = pad.width * scale
            h_px = pad.height * scale

            # Check if this pad is selected
            is_selected = (self._selected_pad == pad)

            # Set pad color (highlight if selected)
            if is_selected:
                painter.setPen(QPen(QColor("#ff6600"), 3))  # Orange highlight
                painter.setBrush(QBrush(QColor("#ffaa00")))  # Lighter orange fill
            else:
                painter.setPen(QPen(self._pad_color, 1))
                painter.setBrush(QBrush(self._pad_color))

            # Draw pad rectangle
            rect = QRectF(
                x_px - w_px / 2,
                y_px - h_px / 2,
                w_px,
                h_px
            )

            # Apply rotation if needed
            if pad.rotation != 0:
                painter.save()
                painter.translate(x_px, y_px)
                painter.rotate(pad.rotation)
                painter.translate(-x_px, -y_px)

            painter.drawRect(rect)

            if pad.rotation != 0:
                painter.restore()

            # Draw pad number
            painter.setPen(QColor("#000000"))  # Black text on gold pad
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, pad.name)

    def _draw_dimensions(self, painter: QPainter, cx: float, cy: float, scale: float):
        """Draw dimension annotations.

        Args:
            painter: QPainter object
            cx: Center X
            cy: Center Y
            scale: Pixels per mm
        """
        if not self._footprint:
            return

        painter.setPen(self._text_color)
        painter.setFont(QFont("Arial", 10))

        # Draw body dimensions in top-left corner
        dims_text = f"Body: {self._footprint.body_width:.2f} x {self._footprint.body_height:.2f} mm"
        painter.drawText(QPointF(10, 20), dims_text)

        # Draw pad count
        pad_count_text = f"Pads: {len(self._footprint.pads)}"
        painter.drawText(QPointF(10, 40), pad_count_text)

    def mousePressEvent(self, event):
        """Handle mouse clicks to select pads.

        Args:
            event: Mouse event
        """
        if not self._footprint:
            return

        # Get click position
        click_x = event.position().x()
        click_y = event.position().y()

        # Check each pad
        for pad in self._footprint.pads:
            # Convert pad position to widget coordinates
            pad_x_px = self._center_x + pad.x * self._scale
            pad_y_px = self._center_y + pad.y * self._scale
            pad_w_px = pad.width * self._scale
            pad_h_px = pad.height * self._scale

            # Create pad rectangle
            pad_rect = QRectF(
                pad_x_px - pad_w_px / 2,
                pad_y_px - pad_h_px / 2,
                pad_w_px,
                pad_h_px
            )

            # Check if click is inside pad
            if pad_rect.contains(click_x, click_y):
                self._selected_pad = pad
                self.pad_clicked.emit(pad)
                self.update()  # Repaint with highlight
                return

        # Click outside any pad - deselect
        self._selected_pad = None
        self.update()
