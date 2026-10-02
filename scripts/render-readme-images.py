#!/usr/bin/env python3
"""Render the README images, app logo and social preview from the real tray icon."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_usage_linux.icon import build_svg  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "img")
FONT = "font-family=\"-apple-system,'Segoe UI',Ubuntu,Cantarell,'DejaVu Sans',sans-serif\""
MONO = "font-family=\"'DejaVu Sans Mono',Menlo,Consolas,monospace\""


def icon(five, weekly, x, y, size, state="ok"):
    """Embed the real icon as a nested <svg> at (x, y)."""
    inner = build_svg(five, weekly, state).strip()
    inner = inner.replace('width="24" height="24"', 'x="%s" y="%s" width="%s" height="%s"' % (x, y, size, size), 1)
    return inner.replace(' xmlns="http://www.w3.org/2000/svg"', "", 1)


def bar(x, y, pct, color, cells=10):
    out = []
    for i in range(cells):
        filled = i < round(pct / 10)
        out.append('<rect x="%d" y="%d" width="13" height="8" rx="2" fill="%s"%s/>'
                   % (x + i * 16, y, color if filled else "#8b949e", "" if filled else ' fill-opacity="0.25"'))
    return "".join(out)


def hero():
    w, h = 820, 300
    p = []
    p.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (w, h, w, h))
    p.append('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
             '<stop offset="0" stop-color="#1f2937"/><stop offset="1" stop-color="#0b1220"/></linearGradient>'
             '<filter id="sh" x="-10%" y="-10%" width="120%" height="130%">'
             '<feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity="0.45"/></filter></defs>')
    p.append('<rect width="%d" height="%d" rx="14" fill="url(#bg)"/>' % (w, h))
    # Panel bar
    p.append('<rect x="0" y="0" width="%d" height="40" rx="14" fill="#111827"/>' % w)
    p.append('<rect x="0" y="26" width="%d" height="14" fill="#111827"/>' % w)
    p.append('<text x="22" y="25" %s font-size="14" font-weight="600" fill="#e5e7eb">Activities</text>' % FONT)
    p.append('<text x="%d" y="25" %s font-size="14" font-weight="600" fill="#e5e7eb" text-anchor="middle">Fri 2 Oct  14:32</text>' % (w // 2, FONT))
    # Highlight behind our icon
    ix = 640
    p.append('<rect x="%d" y="5" width="34" height="30" rx="8" fill="#ffffff" fill-opacity="0.12"/>' % (ix - 5))
    p.append(icon(42, 17, ix, 8, 24))
    # wifi
    p.append('<g transform="translate(690 11)" fill="none" stroke="#e5e7eb" stroke-width="2" stroke-linecap="round">'
             '<path d="M1 7a13 13 0 0 1 16 0"/><path d="M4 10.5a8 8 0 0 1 10 0"/><circle cx="9" cy="14.5" r="1.4" fill="#e5e7eb" stroke="none"/></g>')
    # volume
    p.append('<g transform="translate(720 12)" fill="#e5e7eb"><path d="M0 5h4l5-4v16l-5-4H0z"/>'
             '<path d="M12 4a6 6 0 0 1 0 10" fill="none" stroke="#e5e7eb" stroke-width="2" stroke-linecap="round"/></g>')
    # battery
    p.append('<g transform="translate(752 13)"><rect x="0" y="0" width="24" height="13" rx="3" fill="none" stroke="#e5e7eb" stroke-width="1.6"/>'
             '<rect x="2.5" y="2.5" width="15" height="8" rx="1.5" fill="#e5e7eb"/><rect x="25" y="4" width="2.5" height="5" rx="1" fill="#e5e7eb"/></g>')
    # Dropdown menu
    mx, my, mw = 440, 52, 300
    p.append('<g filter="url(#sh)"><rect x="%d" y="%d" width="%d" height="226" rx="12" fill="#1f2937" stroke="#374151"/></g>' % (mx, my, mw))
    rows = [("5h", 42, "resets in 2h 10m", "#3fb950"), ("Weekly", 17, "resets in 3d 4h", "#3fb950")]
    y = my + 30
    for label, pct, reset, color in rows:
        p.append('<circle cx="%d" cy="%d" r="6" fill="%s"/>' % (mx + 22, y - 4, color))
        p.append('<text x="%d" y="%d" %s font-size="14" font-weight="600" fill="#e5e7eb">%s</text>' % (mx + 36, y, FONT, label))
        p.append(bar(mx + 104, y - 11, pct, color))
        p.append('<text x="%d" y="%d" %s font-size="14" fill="#e5e7eb" text-anchor="end">%d%%</text>' % (mx + mw - 18, y, MONO, pct))
        p.append('<text x="%d" y="%d" %s font-size="12.5" fill="#9ca3af">%s</text>' % (mx + 36, y + 22, FONT, reset))
        y += 58
    p.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#374151"/>' % (mx + 12, y - 12, mx + mw - 12, y - 12))
    for item in ("Refresh now", "Quit"):
        p.append('<text x="%d" y="%d" %s font-size="14" fill="#e5e7eb">%s</text>' % (mx + 22, y + 14, FONT, item))
        y += 34
    # Tagline on the left
    p.append(icon(42, 17, 40, 82, 96))
    p.append('<text x="40" y="218" %s font-size="30" font-weight="700" fill="#f9fafb">claude-usage-linux</text>' % FONT)
    p.append('<text x="40" y="246" %s font-size="15" fill="#9ca3af">Your Claude limits, in the panel.</text>' % FONT)
    p.append("</svg>\n")
    return "".join(p)


def states():
    items = [(42, 17, "ok", "Under 70%"), (78, 55, "ok", "70–89%"), (94, 88, "ok", "90% and up"), (None, None, "error", "Error / offline")]
    w, h = 640, 130
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (w, h, w, h)]
    p.append('<rect width="%d" height="%d" rx="14" fill="#111827"/>' % (w, h))
    for i, (five, weekly, state, label) in enumerate(items):
        cx = 80 + i * 160
        p.append(icon(five, weekly, cx - 28, 18, 56, state))
        p.append('<text x="%d" y="106" %s font-size="13.5" fill="#d1d5db" text-anchor="middle">%s</text>' % (cx, FONT, label))
    p.append("</svg>\n")
    return "".join(p)


def logo():
    """App logo: the two rings on a dark rounded tile, readable on light and dark menus."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'
        '<defs><linearGradient id="t" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#2b3647"/><stop offset="1" stop-color="#0d1421"/></linearGradient></defs>'
        '<rect x="4" y="4" width="120" height="120" rx="28" fill="url(#t)"/>'
        '<circle cx="64" cy="64" r="40" fill="none" stroke="#8b949e" stroke-opacity="0.25" stroke-width="12"/>'
        '<circle cx="64" cy="64" r="40" fill="none" stroke="#3fb950" stroke-width="12" stroke-linecap="round" '
        'pathLength="100" stroke-dasharray="68 100" transform="rotate(-90 64 64)"/>'
        '<circle cx="64" cy="64" r="22" fill="none" stroke="#8b949e" stroke-opacity="0.25" stroke-width="10"/>'
        '<circle cx="64" cy="64" r="22" fill="none" stroke="#d29922" stroke-width="10" stroke-linecap="round" '
        'pathLength="100" stroke-dasharray="40 100" transform="rotate(-90 64 64)"/>'
        "</svg>\n"
    )


def social():
    """1280x640 GitHub social preview: logo, name and tagline."""
    mark = logo().strip().replace(' xmlns="http://www.w3.org/2000/svg" width="128" height="128"',
                                  ' x="120" y="200" width="240" height="240"', 1)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#1f2937"/><stop offset="1" stop-color="#0b1220"/></linearGradient></defs>'
        '<rect width="1280" height="640" fill="url(#bg)"/>' + mark +
        '<text x="420" y="300" %s font-size="72" font-weight="700" fill="#f9fafb">claude-usage-linux</text>' % FONT +
        '<text x="420" y="370" %s font-size="34" fill="#9ca3af">Your Claude limits, in the Linux panel.</text>' % FONT +
        '<text x="420" y="440" %s font-size="26" fill="#6b7280">KDE · GNOME · XFCE · Cinnamon · MATE</text>' % FONT +
        "</svg>\n"
    )


if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), "..", "packaging", "claude-usage-linux.svg"), "w") as f:
        f.write(logo())
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("hero.svg", hero()), ("states.svg", states()), ("social-preview.svg", social())):
        with open(os.path.join(OUT, name), "w") as f:
            f.write(svg)
