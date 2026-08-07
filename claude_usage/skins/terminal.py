"""Direction 1 — Terminal Classic.

htop/btop vibe. Mono everything, box-drawing characters for chrome,
one green accent. ASCII █░ progress bars. High readability, small
chrome, nothing cute.

Nuances that are easy to miss:
- Box-drawing chars (┌─ ╔═ ╚═) must use a mono font that has them in
  its bundled glyphs; JetBrains Mono and Menlo both do. If you see
  boxes render as tofu (□), the font fallback chain failed.
- The green accent only lights up ACTIVE elements (title + LIVE + fills).
  Everything else stays neutral. Resist the urge to green-tint labels.
- Ticker colors are the SAME 4 quartile tiers the existing ticker.py
  emits — we just remap tier 0/1/2/3 to (dim, link, warn, crit).
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFontMetrics, QLinearGradient, QPainter, QPen

from ._paint import (
    draw_ascii_bar, draw_block_bar, draw_heatmap_52w, draw_sparkline_bars,
    draw_text, draw_ticker_marquee, hex_to_qcolor, mono_font,
)
from ._popup import (
    ROW_GAP, SECTION_GAP,
    draw_active_sessions, draw_kpi_big, draw_pct_row, draw_project_list,
    draw_report_card, draw_section_header, draw_sparkline_row,
)


WANTS_TICKER = True
SUPPORTS_OPACITY = True


THEME = {
    "style":          "terminal",
    '_mono_family'    : 'JetBrains Mono',
    '_ui_family'      : 'JetBrains Mono',
    'paper'           : '#0a0f0a',
    'accent2'         : '#87d7d7',
    "bg":             "#0a0f0a",
    "panel":          "#0e1411",
    "border":         "#1d2a22",
    "bar_blue":       "#5fd787",   # accent — used wherever the default theme uses bar_blue
    "bar_track":      "#2e4238",
    "text_primary":   "#d7e3d7",
    "text_secondary": "#7a9889",
    "text_dim":       "#668c75",
    "text_link":      "#87d7d7",
    "separator":      "#1d2a22",
    "warn":           "#d7c85f",
    "crit":           "#ff6b6b",
    "error":          "#ff6b6b",
    "live_indicator": "#5fd787",
    # direction-specific
    "accent":         "#5fd787",
    "very_dim":       "#2e4238",
}

METRICS = {
    "osd_width":       440,
    "osd_height":      172,
    "ticker_height":   28,
    "osd_height_scoped": 212,  # +1 Session/Weekly row footprint (2*line_h + row_gap + 2)
    "codex_rows_height": 80,   # 2 × (osd_height_scoped − osd_height) = two extra rows
    "osd_radius":      6,
    "osd_padding":     12,
    "osd_row_gap":     8,
    "osd_bar_cols":    30,     # ASCII cells in each progress bar
    "popup_width":     540,
    "popup_padding":   18,
    "section_gap":     18,
    "heatmap_cell":    7,
    "heatmap_gap":     2,
}

FONTS = {
    "title_pt":    11,
    "section_pt":  10,
    "body_pt":     10,
    "metric_pt":   18,
    "ticker_pt":   9,
    "family":      "JetBrains Mono",
}


# ---- OSD -----------------------------------------------------------

def _draw_uplink_bar(
    p: QPainter,
    x: float,
    y: float,
    width: float,
    pct: float,
    theme: dict,
    scale: float,
) -> None:
    """Render the Terminal Owl HUD bar with a soft neon fill and dividers."""
    height = max(6.0, 8.0 * scale)
    rect = QRectF(x, y, width, height)
    radius = height / 2
    p.setPen(Qt.NoPen)
    p.setBrush(hex_to_qcolor(theme["bar_track"], 0.98))
    p.drawRoundedRect(rect, radius, radius)

    fill_width = width * max(0.0, min(1.0, pct))
    if fill_width > 0:
        fill = QRectF(x, y, max(height, fill_width), height)
        gradient = QLinearGradient(fill.topLeft(), fill.topRight())
        gradient.setColorAt(0.0, hex_to_qcolor(theme["accent2"]))
        gradient.setColorAt(1.0, hex_to_qcolor(theme["accent"]))
        p.setBrush(gradient)
        p.drawRoundedRect(fill, radius, radius)

    p.setPen(QPen(hex_to_qcolor(theme["accent2"], 0.82), max(0.7, scale * 0.8)))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect, radius, radius)
    p.setPen(QPen(hex_to_qcolor(theme["border"], 0.9), max(0.5, scale * 0.6)))
    for segment in range(1, 6):
        divider_x = x + width * segment / 6
        p.drawLine(QPointF(divider_x, y + scale), QPointF(divider_x, y + height - scale))


def _paint_compact_uplink(
    p: QPainter, rect: QRectF, data, scale: float, theme: dict,
) -> None:
    """Paint a compact HUD: labels and values sit directly above full-width bars."""
    s = scale
    pad = 12 * s
    x = rect.x() + pad
    y = rect.y() + pad
    width = rect.width() - 2 * pad
    family = theme.get("font_family", FONTS["family"])
    title_f = mono_font(10 * s, bold=True, family=family)
    label_f = mono_font(8.5 * s, bold=True, family=family)
    value_f = mono_font(9.5 * s, bold=True, family=family)

    header = theme.get("compact_title", "UPLINK STATUS")
    p.setPen(Qt.NoPen)
    p.setBrush(hex_to_qcolor(theme["bg"], 0.62))
    p.drawRoundedRect(QRectF(x - 4 * s, y - 3 * s, width + 8 * s, 20 * s), 4 * s, 4 * s)
    draw_text(p, x, y + QFontMetrics(title_f).ascent(), header,
              hex_to_qcolor(theme["accent"]), title_f, letter_spacing_px=1.2 * s)
    header_y = y + QFontMetrics(title_f).height() + 4 * s
    p.setPen(QPen(hex_to_qcolor(theme["border"], 0.9), max(0.5, 0.7 * s)))
    p.drawLine(QPointF(x, header_y), QPointF(x + width, header_y))

    rows = [
        ("SESSION", data.session_pct, f"{data.session_reset_min}m · {int(data.session_pct * 100)}%"),
        ("WEEKLY", data.weekly_pct, f"{data.weekly_reset_hrs}h {data.weekly_reset_min}m · {int(data.weekly_pct * 100)}%"),
    ]
    if getattr(data, "scoped_pct", None) is not None and getattr(data, "scoped_label", ""):
        rows.append((
            data.scoped_label.upper(), data.scoped_pct,
            f"{data.scoped_reset_hrs}h {data.scoped_reset_min}m · {int(data.scoped_pct * 100)}%",
        ))
    if getattr(data, "codex_available", False):
        rows.extend([
            ("CODEX 5H", data.codex_session_pct,
             f"{data.codex_session_reset_min}m · {int(data.codex_session_pct * 100)}%"),
            ("CODEX 7D", data.codex_weekly_pct,
             f"{data.codex_weekly_reset_hrs}h {data.codex_weekly_reset_min}m · {int(data.codex_weekly_pct * 100)}%"),
        ])

    row_height = 28 * s
    for index, (label, pct, value) in enumerate(rows):
        top = header_y + 6 * s + index * row_height
        p.setPen(Qt.NoPen)
        p.setBrush(hex_to_qcolor(theme["bg"], 0.58))
        p.drawRoundedRect(
            QRectF(x - 4 * s, top - 2 * s, width + 8 * s, 22 * s),
            4 * s,
            4 * s,
        )
        baseline = top + QFontMetrics(label_f).ascent()
        draw_text(p, x, baseline, label, hex_to_qcolor(theme["text_secondary"]), label_f,
                  letter_spacing_px=0.8 * s)
        value_width = QFontMetrics(value_f).horizontalAdvance(value)
        draw_text(p, x + width - value_width, baseline, value,
                  hex_to_qcolor(theme["text_primary"]), value_f)
        _draw_uplink_bar(p, x, top + QFontMetrics(label_f).height() + 2 * s,
                         width, pct, theme, s)

    if getattr(data, "show_ticker", True):
        ticker_y = rect.bottom() - 10 * s
        p.setPen(QPen(hex_to_qcolor(theme["border"], 0.9), max(0.5, 0.7 * s)))
        p.drawLine(QPointF(x, ticker_y - 14 * s), QPointF(x + width, ticker_y - 14 * s))
        ticker_f = mono_font(8 * s, family=family)
        ticker_colors = (
            theme["text_dim"], theme["text_link"], theme["warn"], theme["crit"],
        )
        draw_ticker_marquee(
            p, x, ticker_y, width,
            data.ticker_items, data.ticker_offset,
            ticker_colors, ticker_f, sep_gap_px=10 * s,
        )


def paint_osd(
    p: QPainter, rect: QRectF, data, scale: float = 1.0, opacity: float = 1.0,
) -> None:
    """Draws the OSD bars view. `data` is the same UsageStats shape the
    existing overlay.py consumes."""
    s = scale
    m = METRICS
    t = THEME
    pad = m["osd_padding"] * s

    # panel
    panel_alpha = max(0.0, min(1.0, opacity))
    radius = m["osd_radius"] * s
    p.setPen(Qt.NoPen)
    if t.get("glass", False):
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, hex_to_qcolor(t["glass_top"], panel_alpha))
        gradient.setColorAt(0.5, hex_to_qcolor(t["panel"], panel_alpha))
        gradient.setColorAt(1.0, hex_to_qcolor(t["glass_bottom"], panel_alpha))
        p.setBrush(gradient)
        p.drawRoundedRect(rect, radius, radius)

        border_alpha = min(1.0, panel_alpha + 0.18)
        p.setPen(QPen(hex_to_qcolor(t["border"], border_alpha), max(1.0, s)))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5 * s, 0.5 * s, -0.5 * s, -0.5 * s), radius, radius)

        p.setPen(QPen(hex_to_qcolor(t["glass_highlight"], panel_alpha * 0.55), max(1.0, s)))
        p.drawLine(
            QPointF(rect.x() + radius, rect.y() + s),
            QPointF(rect.right() - radius, rect.y() + s),
        )
        if t.get("futuristic", False):
            corner = 12 * s
            p.setPen(QPen(hex_to_qcolor(t["accent2"], panel_alpha * 0.7), max(1.0, s)))
            p.drawLine(rect.left() + s, rect.top() + corner, rect.left() + s, rect.top() + s)
            p.drawLine(rect.left() + s, rect.top() + s, rect.left() + corner, rect.top() + s)
            p.drawLine(rect.right() - corner, rect.bottom() - s, rect.right() - s, rect.bottom() - s)
            p.drawLine(rect.right() - s, rect.bottom() - corner, rect.right() - s, rect.bottom() - s)
    else:
        p.setBrush(hex_to_qcolor(t["bg"], panel_alpha))
        p.drawRoundedRect(rect, radius, radius)

    if t.get("compact_hud", False):
        _paint_compact_uplink(p, rect, data, s, t)
        return

    x = rect.x() + pad
    y = rect.y() + pad
    w = rect.width() - pad * 2

    body_f   = mono_font(FONTS["body_pt"] * s, family=FONTS["family"])
    title_f  = mono_font(FONTS["title_pt"] * s, bold=True, family=FONTS["family"])
    ticker_f = mono_font(FONTS["ticker_pt"] * s, family=FONTS["family"])

    fm = QFontMetrics(body_f)
    line_h = fm.height()

    # titlebar  ┌─ CLAUDE  ⚙ N        ● LIVE 10.5k t/m
    baseline = y + fm.ascent()
    title = t.get("title", "┌─ CLAUDE")
    adv = draw_text(p, x, baseline, title, hex_to_qcolor(t["accent"]), title_f, letter_spacing_px=1.0 * s)
    if getattr(data, "subagent_count", 0):
        draw_text(p, x + adv + 8 * s, baseline, f"⚙ {data.subagent_count}",
                  hex_to_qcolor(t["text_secondary"]), body_f)

    live_text = f"● LIVE {data.live_tok_per_min:.1f}k t/m" if getattr(data, "is_live", False) else ""
    if live_text:
        lw = QFontMetrics(body_f).horizontalAdvance(live_text)
        draw_text(p, x + w - lw, baseline, live_text, hex_to_qcolor(t["accent"]), body_f)

    if t.get("futuristic", False):
        p.setPen(QPen(hex_to_qcolor(t["border"], 0.8), max(0.5, s * 0.7)))
        p.drawLine(QPointF(x, y + line_h + 3 * s), QPointF(x + w, y + line_h + 3 * s))

    # session row
    y_row = y + line_h + m["osd_row_gap"] * s
    draw_text(p, x, y_row + fm.ascent(), t.get("session_label", "session"),
              hex_to_qcolor(t["text_secondary"]), body_f)
    right = f"{data.session_reset_min}m · {int(data.session_pct*100)}%"
    rw = fm.horizontalAdvance(right)
    draw_text(p, x + w - rw, y_row + fm.ascent(), right,
              hex_to_qcolor(t["text_secondary"]), body_f)
    y_bar = y_row + line_h + 2 * s
    if t.get("futuristic", False):
        _draw_uplink_bar(p, x, y_bar, fm.horizontalAdvance("█") * m["osd_bar_cols"], data.session_pct, t, s)
    else:
        draw_ascii_bar(p, x, y_bar + fm.ascent(), data.session_pct,
                       m["osd_bar_cols"],
                       hex_to_qcolor(t["accent"]), hex_to_qcolor(t["very_dim"]),
                       body_f)

    # weekly row
    y_row = y_bar + line_h + m["osd_row_gap"] * s
    draw_text(p, x, y_row + fm.ascent(), t.get("weekly_label", "weekly"),
              hex_to_qcolor(t["text_secondary"]), body_f)
    right = f"{data.weekly_reset_hrs}h {data.weekly_reset_min}m · {int(data.weekly_pct*100)}%"
    rw = fm.horizontalAdvance(right)
    draw_text(p, x + w - rw, y_row + fm.ascent(), right,
              hex_to_qcolor(t["text_secondary"]), body_f)
    y_bar = y_row + line_h + 2 * s
    if t.get("futuristic", False):
        _draw_uplink_bar(p, x, y_bar, fm.horizontalAdvance("█") * m["osd_bar_cols"], data.weekly_pct, t, s)
    else:
        draw_ascii_bar(p, x, y_bar + fm.ascent(), data.weekly_pct,
                       m["osd_bar_cols"],
                       hex_to_qcolor(t["accent"]), hex_to_qcolor(t["very_dim"]),
                       body_f)

    # scoped weekly row — optional model-scoped cap (e.g. "fable"). Only
    # drawn when the API reports it; mirrors the weekly row exactly and
    # pushes the ticker below down by one row via the updated y_bar.
    if getattr(data, "scoped_pct", None) is not None and getattr(data, "scoped_label", ""):
        y_row = y_bar + line_h + m["osd_row_gap"] * s
        draw_text(p, x, y_row + fm.ascent(), data.scoped_label.lower(),
                  hex_to_qcolor(t["text_secondary"]), body_f)
        right = f"{data.scoped_reset_hrs}h {data.scoped_reset_min}m · {int(data.scoped_pct*100)}%"
        rw = fm.horizontalAdvance(right)
        draw_text(p, x + w - rw, y_row + fm.ascent(), right,
                  hex_to_qcolor(t["text_secondary"]), body_f)
        y_bar = y_row + line_h + 2 * s
        if t.get("futuristic", False):
            _draw_uplink_bar(p, x, y_bar, fm.horizontalAdvance("█") * m["osd_bar_cols"], data.scoped_pct, t, s)
        else:
            draw_ascii_bar(p, x, y_bar + fm.ascent(), data.scoped_pct,
                           m["osd_bar_cols"],
                           hex_to_qcolor(t["accent"]), hex_to_qcolor(t["very_dim"]),
                           body_f)

    # codex rows — optional second-provider (OpenAI Codex) 5h + 7d windows.
    # Mirrors the session/weekly rows exactly and pushes the ticker below
    # down by two rows via the updated y_bar. Drawn only when active.
    if getattr(data, "codex_available", False):
        # codex 5h — mirrors the session row
        y_row = y_bar + line_h + m["osd_row_gap"] * s
        draw_text(p, x, y_row + fm.ascent(), "codex 5h",
                  hex_to_qcolor(t["text_secondary"]), body_f)
        right = f"{data.codex_session_reset_min}m · {int(data.codex_session_pct*100)}%"
        rw = fm.horizontalAdvance(right)
        draw_text(p, x + w - rw, y_row + fm.ascent(), right,
                  hex_to_qcolor(t["text_secondary"]), body_f)
        y_bar = y_row + line_h + 2 * s
        if t.get("futuristic", False):
            _draw_uplink_bar(p, x, y_bar, fm.horizontalAdvance("█") * m["osd_bar_cols"], data.codex_session_pct, t, s)
        else:
            draw_ascii_bar(p, x, y_bar + fm.ascent(), data.codex_session_pct,
                           m["osd_bar_cols"],
                           hex_to_qcolor(t["accent"]), hex_to_qcolor(t["very_dim"]),
                           body_f)
        # codex 7d — mirrors the weekly row
        y_row = y_bar + line_h + m["osd_row_gap"] * s
        draw_text(p, x, y_row + fm.ascent(), "codex 7d",
                  hex_to_qcolor(t["text_secondary"]), body_f)
        right = f"{data.codex_weekly_reset_hrs}h {data.codex_weekly_reset_min}m · {int(data.codex_weekly_pct*100)}%"
        rw = fm.horizontalAdvance(right)
        draw_text(p, x + w - rw, y_row + fm.ascent(), right,
                  hex_to_qcolor(t["text_secondary"]), body_f)
        y_bar = y_row + line_h + 2 * s
        if t.get("futuristic", False):
            _draw_uplink_bar(p, x, y_bar, fm.horizontalAdvance("█") * m["osd_bar_cols"], data.codex_weekly_pct, t, s)
        else:
            draw_ascii_bar(p, x, y_bar + fm.ascent(), data.codex_weekly_pct,
                           m["osd_bar_cols"],
                           hex_to_qcolor(t["accent"]), hex_to_qcolor(t["very_dim"]),
                           body_f)

    if getattr(data, "show_ticker", True):
        # Ticker strip — dashed separator + colour-quartile cost tags.
        y_tick = y_bar + line_h + 6 * s
        p.setPen(hex_to_qcolor(t["border"]))
        dash_w = 3 * s
        gx = x
        while gx < x + w:
            p.drawLine(QPointF(gx, y_tick), QPointF(gx + dash_w, y_tick))
            gx += dash_w * 2

        ticker_colors = (t["text_dim"], t["text_link"], t["warn"], t["crit"])
        y_tick_base = y_tick + 4 * s + QFontMetrics(ticker_f).ascent()
        draw_ticker_marquee(
            p, x, y_tick_base, w,
            data.ticker_items, data.ticker_offset,
            ticker_colors, ticker_f, sep_gap_px=10 * s,
        )


# ---- POPUP ---------------------------------------------------------

def measure_popup(data, scale: float = 1.0) -> int:
    """Exact popup height via dry paint — see ``_popup.dry_measure``."""
    from ._popup import dry_measure
    return dry_measure(paint_popup, data, scale, METRICS["popup_width"]) + int(20 * scale)


def paint_loading(p: QPainter, rect: QRectF, phase: float = 0.0,
                  scale: float = 1.0) -> None:
    from ._popup import paint_loading as _pl
    _pl(p, rect, THEME, scale, style="terminal", phase=phase)


def paint_popup(p: QPainter, rect: QRectF, data, scale: float = 1.0) -> float:
    """Terminal-style popup. Uses [NN] section headers and ASCII bars.
    Mimics a terminal readout — dashed rules, box-drawing trim, mono everywhere."""
    s = scale; t = THEME
    pad = 18 * s

    # paper
    p.setPen(Qt.NoPen); p.setBrush(hex_to_qcolor(t["bg"]))
    p.drawRoundedRect(rect, 6 * s, 6 * s)
    p.setPen(hex_to_qcolor(t["border"])); p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6 * s, 6 * s)

    x = rect.x() + pad; y = rect.y() + pad
    w = rect.width() - pad * 2

    # masthead — box-drawing banner
    banner_f = mono_font(12 * s, bold=True, family=FONTS["family"])
    fm = QFontMetrics(banner_f)
    banner = "╔═ CLAUDE USAGE " + "═" * 12 + "╗"
    draw_text(p, x, y + fm.ascent(), banner,
              hex_to_qcolor(t["accent"]), banner_f,
              letter_spacing_px=1.5 * s)
    sub_f = mono_font(10 * s, family=FONTS["family"])
    draw_text(p, x, y + fm.height() + QFontMetrics(sub_f).ascent() + 4 * s,
              "last updated: just now · refresh: 30s",
              hex_to_qcolor(t["text_dim"]), sub_f)
    y += fm.height() + QFontMetrics(sub_f).height() + 14 * s

    # [01] plan limits
    y = draw_section_header(p, x, y, w, 1, "plan limits", t, s, style="terminal")
    y = draw_pct_row(p, x, y, w, "session · resets in " + f"{data.session_reset_min}m",
                     data.session_pct, f"{int(data.session_pct * 100)}%".rjust(4),
                     t, s, bar_style="ascii", fill_hex=t["accent"], ascii_cols=46)
    y = draw_sparkline_row(p, x, y, w, 28 * s, data.spark_5h,
                           "last 5 hours", t, s)
    y += ROW_GAP * s
    y = draw_pct_row(p, x, y, w, "weekly · resets " + data.weekly_reset_label,
                     data.weekly_pct, f"{int(data.weekly_pct * 100)}%".rjust(4),
                     t, s, bar_style="ascii", fill_hex=t["accent"], ascii_cols=46)
    y = draw_sparkline_row(p, x, y, w, 24 * s, data.spark_7d,
                           "last 7 days", t, s)
    # Optional model-scoped weekly cap (e.g. Fable) — only when present.
    if getattr(data, "scoped_pct", None) is not None:
        y += ROW_GAP * s
        label = (data.scoped_label or "scoped").lower()
        reset = data.scoped_reset_label or ""
        y = draw_pct_row(p, x, y, w,
                         (f"{label} weekly · resets " + reset).rstrip(),
                         data.scoped_pct, f"{int(data.scoped_pct * 100)}%".rjust(4),
                         t, s, bar_style="ascii", fill_hex=t["warn"], ascii_cols=46)
    # Peak-window hint — unobtrusive dim line under the plan-limit rows.
    if getattr(data, "in_peak", False) and getattr(data, "peak_hint", ""):
        y += ROW_GAP * s
        _pf = mono_font(9 * s, family=FONTS["family"])
        _fmp = QFontMetrics(_pf)
        draw_text(p, x, y + _fmp.ascent(), "» " + data.peak_hint.lower(),
                  hex_to_qcolor(t["text_dim"]), _pf)
        y += _fmp.height()
    y += SECTION_GAP * s

    # [02] calendar (52-week heatmap)
    y = draw_section_header(p, x, y, w, 2, "calendar", t, s, style="terminal")
    draw_heatmap_52w(p, x, y, data.heat_52w,
                     cell=7 * s, gap=2 * s,
                     track=hex_to_qcolor(t["very_dim"]),
                     fill_hex=t["accent"])
    y += (7 + 2) * 7 * s + 6 * s
    draw_text(p, x, y + QFontMetrics(sub_f).ascent(),
              "last 52 weeks", hex_to_qcolor(t["text_dim"]), sub_f)
    y += QFontMetrics(sub_f).height() + SECTION_GAP * s

    # [03] cost
    y = draw_section_header(p, x, y, w, 3, "cost (today)", t, s, style="terminal")
    big_f = mono_font(22 * s, bold=True, family=FONTS["family"])
    fm_b = QFontMetrics(big_f)
    cost_txt = f"${data.cost_today_usd:.2f}"
    draw_text(p, x, y + fm_b.ascent(), cost_txt,
              hex_to_qcolor(t["accent"]), big_f)
    sub_text = f"{data.plan} · ${data.cache_saved_usd:,.0f} saved by cache"
    sw = QFontMetrics(sub_f).horizontalAdvance(sub_text)
    draw_text(p, x + w - sw, y + fm_b.ascent(), sub_text,
              hex_to_qcolor(t["text_dim"]), sub_f)
    y += fm_b.height() + 6 * s
    # Monthly budget line under the big today-cost figure (only when a cap set).
    if getattr(data, "month_budget_usd", 0.0) > 0 and getattr(data, "budget_line", ""):
        _bf = mono_font(10 * s, family=FONTS["family"])
        _fmb = QFontMetrics(_bf)
        _bc = t.get("warn", t["accent"]) if getattr(data, "budget_over", False) else t["text_dim"]
        draw_text(p, x, y + _fmb.ascent(), "» " + data.budget_line,
                  hex_to_qcolor(_bc), _bf)
        y += _fmb.height() + 4 * s
    # model + rows
    mono_f = mono_font(10 * s, family=FONTS["family"])
    fm_m = QFontMetrics(mono_f)
    draw_text(p, x, y + fm_m.ascent(), data.cost_model,
              hex_to_qcolor(t["text_secondary"]), mono_f)
    y += fm_m.height() + 2 * s
    for row in data.cost_rows:
        left = f"  {row.label:<12} {row.tokens} × {row.rate}"
        right = f"${row.value_usd:.2f}"
        rw = fm_m.horizontalAdvance(right)
        draw_text(p, x, y + fm_m.ascent(), left,
                  hex_to_qcolor(t["text_primary"]), mono_f)
        draw_text(p, x + w - rw, y + fm_m.ascent(), right,
                  hex_to_qcolor(t["text_primary"]), mono_f)
        y += fm_m.height() + 2 * s
    y += SECTION_GAP * s

    # [04] top projects
    y = draw_section_header(p, x, y, w, 4, "top projects", t, s, style="terminal")
    y = draw_project_list(p, x, y, w, data.top_projects, t, s)
    y += SECTION_GAP * s

    # [05] tips
    y = draw_section_header(p, x, y, w, 5, "tips", t, s, style="terminal")
    tip_f = mono_font(10 * s, family=FONTS["family"])
    fm_t = QFontMetrics(tip_f)
    for tip in data.tips:
        draw_text(p, x, y + fm_t.ascent(), "▸",
                  hex_to_qcolor(t["warn"]), tip_f)
        p.setPen(hex_to_qcolor(t["text_primary"]))
        p.setFont(tip_f)
        tr = QRectF(x + 14 * s, y, w - 14 * s, 1000)
        br = p.fontMetrics().boundingRect(tr.toRect(), Qt.TextWordWrap, tip)
        p.drawText(QRectF(x + 14 * s, y + fm_t.ascent(), w - 14 * s, br.height()),
                   Qt.TextWordWrap, tip)
        y += max(fm_t.height(), br.height()) + 4 * s
    y += SECTION_GAP * s

    # [06] weekly report
    y = draw_section_header(p, x, y, w, 6, "your week", t, s, style="terminal")
    y = draw_report_card(p, x, y, w, data.weekly_report, t, s, style="quote")
    y += SECTION_GAP * s

    # [07] active sessions
    y = draw_section_header(p, x, y, w, 7, "active sessions", t, s, style="terminal")
    y = draw_active_sessions(p, x, y, w, data.active_sessions, t, s)

    # bottom trim
    y += 10 * s
    trim = "╚" + "═" * 28 + "╝"
    fm_tr = QFontMetrics(sub_f)
    tw = fm_tr.horizontalAdvance(trim)
    draw_text(p, x + (w - tw) / 2, y + fm_tr.ascent(), trim,
              hex_to_qcolor(t["text_dim"]), sub_f)
    return y + fm_tr.height() + pad


# Constant used by the popup helpers above (ROW_GAP from _popup.py).
ROW_GAP = 6
