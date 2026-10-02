"""Usage window: two large rings that sweep to the current usage.

draw() is plain Cairo so it can be rendered and tested without a display.
"""

import math
from datetime import datetime

from .icon import COLORS, GREY
from .usage import STATUS, format_reset, reset_at, severity

WIDTH, HEIGHT = 480, 270
ANIMATION_SECONDS = 0.9


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _text(cr, text, cx, y, size, rgba, bold=False):
    import cairo
    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    ext = cr.text_extents(text)
    cr.set_source_rgba(*rgba)
    cr.move_to(cx - ext.width / 2 - ext.x_bearing, y)
    cr.show_text(text)
    return ext


def _card(cr, x, y, w, h, title, window, shown, message, now):
    sev = severity(window.percent) if message is None else "unknown"
    color = _rgb(COLORS.get(sev, GREY))
    cx, cy, r = x + w / 2, y + 74, 50

    _rounded_rect(cr, x, y, w, h, 18)
    cr.set_source_rgba(1, 1, 1, 0.05)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, 0.08)
    cr.set_line_width(1)
    cr.stroke()

    cr.set_line_cap(1)  # round
    cr.set_source_rgba(*_rgb(GREY), 0.22)
    cr.set_line_width(12)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    if message is None and shown > 0:
        end = -math.pi / 2 + 2 * math.pi * min(shown, 100) / 100
        cr.set_source_rgba(*color, 0.18)  # soft glow under the arc
        cr.set_line_width(22)
        cr.arc(cx, cy, r, -math.pi / 2, end)
        cr.stroke()
        cr.set_source_rgb(*color)
        cr.set_line_width(12)
        cr.arc(cx, cy, r, -math.pi / 2, end)
        cr.stroke()

    white, dim, faint = (0.98, 0.98, 0.99, 1), (0.65, 0.68, 0.72, 1), (0.45, 0.48, 0.53, 1)
    if message is not None or window.percent is None:
        _text(cr, "!" if message is not None else "n/a", cx, cy + 10, 28, dim, bold=True)
    else:
        _text(cr, "%d%%" % round(shown), cx, cy + 10, 28, white, bold=True)

    _text(cr, title, cx, y + 158, 15, white, bold=True)

    # Status pill, coloured by severity.
    label = STATUS[sev]
    import cairo
    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(11)
    pw = cr.text_extents(label).width + 20
    _rounded_rect(cr, cx - pw / 2, y + 168, pw, 20, 10)
    cr.set_source_rgba(*color, 0.18)
    cr.fill()
    _text(cr, label, cx, y + 182, 11, (*color, 1), bold=True)

    if message is None and window.resets_at is not None:
        _text(cr, "Resets in " + format_reset(window.resets_at, now), cx, y + 208, 12.5, dim)
        _text(cr, reset_at(window.resets_at, now), cx, y + 226, 11.5, faint)


def draw(cr, width, height, windows, shown, message=None, now=None):
    """Paint the window. windows: [(title, UsageWindow)]; shown: animated percents."""
    import cairo
    now = now or datetime.now().astimezone()
    bg = cairo.LinearGradient(0, 0, width, height)
    bg.add_color_stop_rgb(0, *_rgb("#1f2937"))
    bg.add_color_stop_rgb(1, *_rgb("#0b1220"))
    cr.set_source(bg)
    cr.paint()

    pad = 16
    card_w = (width - pad * 3) / 2
    card_h = height - pad * 2 - (22 if message else 0)
    for i, (title, window) in enumerate(windows):
        _card(cr, pad + i * (card_w + pad), pad, card_w, card_h, title, window, shown[i],
              message, now)
    if message:
        _text(cr, message, width / 2, height - 14, 12.5, (0.85, 0.6, 0.35, 1))


class DetailsWindow:
    """GTK window around draw(). Closing it only hides it."""

    def __init__(self, Gtk, GLib, on_refresh):
        self.Gtk, self.GLib = Gtk, GLib
        from .usage import UsageWindow
        self.windows = [("5-hour", UsageWindow()), ("Weekly", UsageWindow())]
        self.message = "Loading…"
        self.shown = [0.0, 0.0]
        self.start = [0.0, 0.0]
        self.t0 = None

        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)
        self.win = Gtk.Window(title="Claude Monitoring")
        self.win.set_icon_name("claude-monitoring")
        self.win.set_resizable(False)
        self.win.set_position(Gtk.WindowPosition.CENTER)
        self.header = Gtk.HeaderBar(title="Claude Monitoring", show_close_button=True)
        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        refresh.set_tooltip_text("Refresh now")
        refresh.connect("clicked", lambda _b: on_refresh())
        self.header.pack_end(refresh)
        self.win.set_titlebar(self.header)

        self.area = Gtk.DrawingArea()
        self.area.set_size_request(WIDTH, HEIGHT)
        self.area.connect("draw", self._on_draw)
        self.win.add(self.area)
        self.win.connect("delete-event", lambda *_a: self.win.hide() or True)
        self.win.connect("key-press-event", self._on_key)
        # Keep the reset countdowns current while the window is open.
        GLib.timeout_add_seconds(30, self._tick_minutes)

    def present(self):
        if not self.win.get_visible():
            self.shown = [0.0, 0.0]
            self.win.show_all()
            self._animate()
        self.win.present()

    def update(self, five, weekly, message, updated):
        from .usage import UsageWindow
        if message is not None:
            five, weekly = UsageWindow(), UsageWindow()
        self.windows = [("5-hour", five), ("Weekly", weekly)]
        self.message = message
        self.header.set_subtitle(updated)
        if self.win.get_visible():
            self._animate()

    def _targets(self):
        return [w.percent or 0.0 for _t, w in self.windows]

    def _animate(self):
        self.start = list(self.shown)
        self.t0 = None
        self.area.add_tick_callback(self._on_tick)

    def _on_tick(self, _widget, clock):
        now = clock.get_frame_time()
        if self.t0 is None:
            self.t0 = now
        k = ease_out((now - self.t0) / 1e6 / ANIMATION_SECONDS)
        self.shown = [a + (b - a) * k for a, b in zip(self.start, self._targets())]
        self.area.queue_draw()
        return k < 1

    def _tick_minutes(self):
        if self.win.get_visible():
            self.area.queue_draw()
        return True

    def _on_key(self, _w, event):
        if event.keyval == self.Gtk.accelerator_parse("Escape")[0]:
            self.win.hide()
        return False

    def _on_draw(self, widget, cr):
        draw(cr, widget.get_allocated_width(), widget.get_allocated_height(),
             self.windows, self.shown, self.message)
        return False
