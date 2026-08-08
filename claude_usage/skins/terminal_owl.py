"""Night Owl palette rendered with the existing terminal skin layout."""

from __future__ import annotations

from contextlib import contextmanager

from . import terminal

WANTS_TICKER = terminal.WANTS_TICKER
SUPPORTS_OPACITY = terminal.SUPPORTS_OPACITY
METRICS = {
    **terminal.METRICS,
    "osd_width": 270,
    "osd_height": 112,
    "osd_height_scoped": 144,
    "codex_rows_height": 32,
    "ticker_height": 28,
    "gauge_width": 270,
    "gauge_height": 146,
    "gauge_codex_height": 0,
    "gauge_scoped_height": 28,
}
FONTS = terminal.FONTS

THEME = {
    **terminal.THEME,
    "style": "terminal-owl",
    "paper": "#011627",
    "bg": "#011627",
    "panel": "#011b30",
    "glass": True,
    "futuristic": True,
    "compact_hud": True,
    "weekly_only": True,
    "compact_title": "[ CLAUDE // UPLINK ]",
    "font_family": "Noto Sans Mono",
    "glass_top": "#0b2d4a",
    "glass_bottom": "#010f1e",
    "glass_highlight": "#7fdbca",
    "border": "#1d3b53",
    "bar_blue": "#82aaff",
    "bar_track": "#0a3451",
    "text_primary": "#d6deeb",
    "text_secondary": "#a9b7c6",
    "text_dim": "#5f7e97",
    "text_link": "#7fdbca",
    "separator": "#1d3b53",
    "warn": "#ffcb8b",
    "crit": "#f78c6c",
    "error": "#ef5350",
    "live_indicator": "#addb67",
    "accent": "#82aaff",
    "accent2": "#7fdbca",
    "title": "[ CLAUDE // UPLINK ]",
    "session_label": "SESSION",
    "weekly_label": "WEEKLY",
    "very_dim": "#02233d",
}


@contextmanager
def _terminal_palette():
    """Reuse terminal drawing while swapping only its palette for this paint."""
    previous = terminal.THEME
    terminal.THEME = THEME
    try:
        yield
    finally:
        terminal.THEME = previous


def paint_osd(*args, **kwargs):
    with _terminal_palette():
        return terminal.paint_osd(*args, **kwargs)


def paint_gauge(*args, **kwargs):
    with _terminal_palette():
        return terminal.paint_gauge(*args, **kwargs)


def measure_popup(*args, **kwargs):
    return terminal.measure_popup(*args, **kwargs)


def paint_loading(*args, **kwargs):
    with _terminal_palette():
        return terminal.paint_loading(*args, **kwargs)


def paint_popup(*args, **kwargs):
    with _terminal_palette():
        return terminal.paint_popup(*args, **kwargs)
