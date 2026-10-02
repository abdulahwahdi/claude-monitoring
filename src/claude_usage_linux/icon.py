"""Render the dual-ring tray icon as SVG. No GTK here."""

import glob
import os

from .usage import severity

COLORS = {"ok": "#3fb950", "warn": "#d29922", "crit": "#f85149"}
GREY = "#8b949e"
TRACK_OPACITY = "0.25"
OUTER = (10.0, 2.4)
INNER = (6.5, 2.0)


def cache_dir(env=os.environ) -> str:
    base = env.get("XDG_RUNTIME_DIR")
    if base and os.path.isdir(base):
        path = os.path.join(base, "claude-usage-linux")
    else:
        path = os.path.join(os.path.expanduser("~/.cache"), "claude-usage-linux")
    os.makedirs(path, exist_ok=True)
    return path


def _ring(radius, width, percent, color):
    parts = [
        '<circle cx="12" cy="12" r="%s" fill="none" stroke="%s" '
        'stroke-opacity="%s" stroke-width="%s"/>' % (radius, GREY, TRACK_OPACITY, width)
    ]
    if percent is not None and percent > 0:
        p = max(0.0, min(100.0, float(percent)))
        parts.append(
            '<circle cx="12" cy="12" r="%s" fill="none" stroke="%s" stroke-width="%s" '
            'stroke-linecap="round" pathLength="100" stroke-dasharray="%.2f 100" '
            'transform="rotate(-90 12 12)"/>' % (radius, color, width, p)
        )
    return "".join(parts)


def build_svg(five_pct, weekly_pct, state="ok") -> str:
    if state == "error":
        outer = _ring(*OUTER, None, GREY)
        inner = _ring(*INNER, None, GREY)
        text, fill = "!", GREY
    else:
        outer = _ring(*OUTER, five_pct, COLORS.get(severity(five_pct), GREY))
        inner = _ring(*INNER, weekly_pct, COLORS.get(severity(weekly_pct), GREY))
        if five_pct is None:
            text, fill = "!", GREY
        else:
            text, fill = str(int(round(five_pct))), "#ffffff"
    size = 6 if len(text) >= 3 else 7.5
    label = (
        '<text x="12" y="12" text-anchor="middle" dominant-baseline="central" '
        'font-family="sans-serif" font-weight="bold" font-size="%s" fill="%s">%s</text>'
        % (size, fill, text)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24">%s%s%s</svg>\n' % (outer, inner, label)
    )


def _tag(pct):
    return "na" if pct is None else str(int(round(pct)))


def render_icon(five_pct, weekly_pct, state="ok", directory=None) -> str:
    directory = directory or cache_dir()
    os.makedirs(directory, exist_ok=True)
    if state == "error":
        name = "icon-error.svg"
    else:
        name = "icon-%s-%s.svg" % (_tag(five_pct), _tag(weekly_pct))
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_svg(five_pct, weekly_pct, state))
    for old in glob.glob(os.path.join(directory, "icon-*.svg")):
        if old != path:
            try:
                os.remove(old)
            except OSError:
                pass
    return path
