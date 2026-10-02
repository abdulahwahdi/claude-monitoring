"""GTK / AppIndicator wiring for the tray app."""

import os
import signal
import sys
import threading
from datetime import datetime

from . import __version__, icon, instance, update
from .details import DetailsWindow
from .config import load_config
from .login import NoTerminal, launch_login
from .usage import (AuthError, BadCredentials, NoCredentials, Offline, RateLimited,
                    TokenExpired, Usage, UsageWindow, fetch_usage, menu_lines,
                    load_token, needs_login, parse_usage)

MAX_BACKOFF = 15 * 60
NO_TERMINAL_MSG = "No terminal found — run `claude auth login` manually"


def error_message(exc) -> str:
    if isinstance(exc, (NoCredentials, BadCredentials)):
        return "Not logged in — click Log in…"
    if isinstance(exc, (TokenExpired, AuthError)):
        return "Token expired — click Log in…"
    if isinstance(exc, RateLimited):
        return "Rate limited — backing off"
    if isinstance(exc, Offline):
        return "Offline"
    return "Error: %s" % exc.__class__.__name__


def fetch_once(credentials_path):
    """Return (Usage, None) or (None, exception). Runs in a worker thread."""
    try:
        token = load_token(credentials_path)
        return parse_usage(fetch_usage(token)), None
    except Exception as exc:  # noqa: BLE001 - surfaced in the menu
        return None, exc


def _import_gi():
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_foreign("cairo")  # the usage window draws with Cairo
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3 as AppIndicator
        except (ValueError, ImportError):
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3 as AppIndicator
        from gi.repository import GLib, Gtk
    except (ImportError, ValueError) as exc:
        print("claude-monitoring needs PyGObject, GTK 3 and AppIndicator typelibs (%s).\n"
              "Debian/Ubuntu: sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 "
              "gir1.2-ayatanaappindicator3-0.1" % exc, file=sys.stderr)
        sys.exit(1)
    return Gtk, GLib, AppIndicator


class TrayApp:
    def __init__(self):
        self.Gtk, self.GLib, AppIndicator = _import_gi()
        Gtk = self.Gtk
        self.config = load_config()
        self.interval = self.config.poll_interval_seconds
        self.timer_id = None
        self.busy = False
        self.last_error = None

        self.icon_dir = icon.cache_dir()
        path = icon.render_icon(None, None, "error", self.icon_dir)
        self.indicator = AppIndicator.Indicator.new(
            "claude-monitoring", os.path.splitext(os.path.basename(path))[0],
            AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_icon_theme_path(self.icon_dir)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.details = DetailsWindow(Gtk, self.GLib, self.refresh)
        self.menu = Gtk.Menu()
        show = Gtk.MenuItem(label="Show usage window")
        show.connect("activate", lambda _w: self.details.present())
        self.menu.append(show)
        self.menu.append(Gtk.SeparatorMenuItem())
        # Per window: a row with a ring icon, then its reset line.
        self.info = []
        self.rings = []
        for i in range(4):
            if i % 2 == 0:
                image = Gtk.Image()
                item = Gtk.ImageMenuItem(label="")
                item.set_image(image)
                item.set_always_show_image(True)
                self.rings.append(image)
            else:
                item = Gtk.MenuItem(label="")
            item.set_sensitive(False)
            self.menu.append(item)
            self.info.append(item)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.status = Gtk.MenuItem(label="Loading…")
        self.status.set_sensitive(False)
        self.menu.append(self.status)
        self.login_item = Gtk.MenuItem(label="Log in…")
        self.login_item.connect("activate", self.on_login)
        self.menu.append(self.login_item)
        refresh = Gtk.MenuItem(label="Refresh now")
        refresh.connect("activate", lambda _w: self.refresh())
        self.menu.append(refresh)
        if update.installed_from_package():
            update_item = Gtk.MenuItem(label="Update now")
            update_item.connect("activate", self.on_update)
        else:
            update_item = Gtk.MenuItem(label=update.PIP_HINT)
            update_item.set_sensitive(False)
        self.menu.append(update_item)
        self.menu.append(Gtk.SeparatorMenuItem())
        version = Gtk.MenuItem(label="Version " + __version__)
        version.set_sensitive(False)
        self.menu.append(version)
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _w: Gtk.main_quit())
        self.menu.append(quit_item)
        self.menu.show_all()
        self.login_item.hide()
        self.indicator.set_menu(self.menu)
        # Middle-click on the icon opens the window where the panel supports it.
        self.indicator.set_secondary_activate_target(show)

    def start(self):
        self.GLib.unix_signal_add(self.GLib.PRIORITY_DEFAULT, signal.SIGINT, self.Gtk.main_quit)
        # A second launch sends SIGUSR1 to open the window here instead.
        self.GLib.unix_signal_add(self.GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.on_show)
        self.refresh()
        self.schedule()
        self.Gtk.main()

    def schedule(self):
        if self.timer_id is not None:
            self.GLib.source_remove(self.timer_id)
        self.timer_id = self.GLib.timeout_add_seconds(self.interval, self.on_timer)

    def on_timer(self):
        self.refresh()
        return True

    def refresh(self):
        if self.busy:
            return
        self.busy = True

        def work():
            result = fetch_once(self.config.credentials_path)
            self.GLib.idle_add(self.update_ui, result)

        threading.Thread(target=work, daemon=True).start()

    def on_login(self, _widget):
        try:
            launch_login(self.config.login_command,
                         on_exit=lambda: self.GLib.idle_add(self.refresh_idle))
        except NoTerminal:
            self.status.set_label(NO_TERMINAL_MSG)

    def on_show(self):
        self.details.present()
        return True

    def on_update(self, _widget):
        try:
            launch_login(update.UPDATE_COMMAND,
                         on_exit=lambda: self.GLib.idle_add(self.restart))
        except NoTerminal:
            self.status.set_label("No terminal found — run: " + update.UPDATE_COMMAND)

    def restart(self):
        """Re-exec so a freshly installed version takes over. The lock fd is
        not inheritable, so the new process can take the lock."""
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def refresh_idle(self):
        self.refresh()
        return False

    def set_lines(self, five: UsageWindow, weekly: UsageWindow, placeholder=False):
        now = datetime.now().astimezone()
        lines = []
        for slot, (name, window) in enumerate((("5-hour", five), ("Weekly", weekly))):
            l1, l2 = menu_lines(name, window, now)
            if placeholder:
                l1, l2 = "%s   —" % name, ""
            lines += [l1, l2]
            self.rings[slot].set_from_file(
                icon.render_ring(slot, None if placeholder else window.percent, self.icon_dir))
        for item, text in zip(self.info, lines):
            item.set_label(text)
            if text:
                item.show()
            else:
                item.hide()

    def update_ui(self, result):
        self.busy = False
        usage, exc = result
        self.last_error = exc
        if exc is None:
            five, weekly = usage.five_hour, usage.weekly
            self.set_lines(five, weekly)
            updated = "Updated " + datetime.now().strftime("%H:%M")
            self.status.set_label(updated)
            self.details.update(five, weekly, None, updated)
            path = icon.render_icon(five.percent, weekly.percent, "ok", self.icon_dir)
            label = "%d%%" % round(five.percent) if five.percent is not None else ""
            tip = "Claude usage — 5h: %s, weekly: %s" % (
                _pct(five.percent), _pct(weekly.percent))
            if self.interval != self.config.poll_interval_seconds:
                self.interval = self.config.poll_interval_seconds
                self.schedule()
        else:
            self.set_lines(UsageWindow(), UsageWindow(), placeholder=True)
            self.status.set_label(error_message(exc))
            self.details.update(None, None, error_message(exc), "")
            path = icon.render_icon(None, None, "error", self.icon_dir)
            label = ""
            tip = "Claude usage — " + error_message(exc)
            if isinstance(exc, RateLimited):
                self.interval = min(self.interval * 2, MAX_BACKOFF)
                self.schedule()
        if needs_login(exc):
            self.login_item.show()
        else:
            self.login_item.hide()
        name = os.path.splitext(os.path.basename(path))[0]
        self.indicator.set_icon_full(name, tip)
        self.indicator.set_label(label, "100%")
        self.indicator.set_title(tip)
        return False


def _pct(p):
    return "n/a" if p is None else "%d%%" % round(p)


def main():
    lock = instance.acquire(icon.cache_dir())
    if lock is None:
        if instance.notify_running(icon.cache_dir()):
            print("claude-monitoring is already running; showing its window.")
        else:
            print("claude-monitoring is already running.")
        return
    TrayApp().start()


if __name__ == "__main__":
    main()
