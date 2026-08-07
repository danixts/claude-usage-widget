"""Night Owl palette rendered with the existing terminal skin layout."""

from __future__ import annotations

from contextlib import contextmanager

from . import terminal

WANTS_TICKER = terminal.WANTS_TICKER
SUPPORTS_OPACITY = terminal.SUPPORTS_OPACITY
METRICS = terminal.METRICS
FONTS = terminal.FONTS

THEME = {
    **terminal.THEME,
    "style": "terminal-owl",
    "paper": "#011627",
    "bg": "#011627",
    "panel": "#011b30",
    "border": "#1d3b53",
    "bar_blue": "#82aaff",
    "bar_track": "#02233d",
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


def measure_popup(*args, **kwargs):
    return terminal.measure_popup(*args, **kwargs)


def paint_loading(*args, **kwargs):
    with _terminal_palette():
        return terminal.paint_loading(*args, **kwargs)


def paint_popup(*args, **kwargs):
    with _terminal_palette():
        return terminal.paint_popup(*args, **kwargs)
