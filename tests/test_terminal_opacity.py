# ruff: noqa: I001

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from claude_usage.skins import terminal, terminal_owl


_app = QApplication.instance() or QApplication([])


def _data() -> SimpleNamespace:
    return SimpleNamespace(
        subagent_count=0,
        is_live=False,
        live_tok_per_min=0.0,
        session_reset_min=60,
        session_pct=0.5,
        weekly_reset_hrs=12,
        weekly_reset_min=30,
        weekly_pct=0.5,
        scoped_pct=None,
        scoped_label="",
        codex_available=False,
        ticker_items=[],
        ticker_offset=0.0,
    )


def _background_alpha(skin, opacity: float) -> int:
    image = QImage(440, 172, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    skin.paint_osd(painter, QRectF(0, 0, 440, 172), _data(), opacity=opacity)
    painter.end()
    return image.pixelColor(5, 5).alpha()


def _background_colors(skin, opacity: float):
    image = QImage(440, 172, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    skin.paint_osd(painter, QRectF(0, 0, 440, 172), _data(), opacity=opacity)
    painter.end()
    return image.pixelColor(355, 20), image.pixelColor(355, 150)


def _render_bytes(skin, data: SimpleNamespace) -> bytes:
    image = QImage(440, 172, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    skin.paint_osd(painter, QRectF(0, 0, 440, 172), data, opacity=0.25)
    painter.end()
    return bytes(image.constBits())


def test_terminal_skin_applies_osd_opacity():
    assert 55 <= _background_alpha(terminal, 0.25) <= 75


def test_terminal_owl_skin_applies_osd_opacity():
    assert 55 <= _background_alpha(terminal_owl, 0.25) <= 75


def test_terminal_owl_uses_a_translucent_glass_gradient():
    top, bottom = _background_colors(terminal_owl, 0.25)
    assert top.alpha() > 0
    assert bottom.alpha() > 0
    assert top.rgb() != bottom.rgb()


def test_terminal_skin_hides_bottom_ticker_when_disabled():
    shown = _render_bytes(terminal, _data())
    hidden_data = _data()
    hidden_data.show_ticker = False
    hidden = _render_bytes(terminal, hidden_data)
    assert shown != hidden
