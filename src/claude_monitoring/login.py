"""Launch a terminal running the login command. No GTK here."""

import os
import shlex
import shutil
import subprocess
import threading

TERMINALS = [
    "x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal",
    "mate-terminal", "tilix", "kitty", "alacritty", "xterm",
]


class NoTerminal(Exception):
    pass


def find_terminal(which=shutil.which, env=os.environ):
    candidates = []
    term = env.get("TERMINAL")
    if term:
        candidates.append(term)
    candidates.extend(TERMINALS)
    for name in candidates:
        if which(name):
            return name
    return None


def build_login_argv(terminal, command):
    inner = "%s; echo; read -p 'Press Enter to close' _" % command
    shell = ["sh", "-c", inner]
    base = os.path.basename(terminal)
    if base in ("gnome-terminal", "mate-terminal"):
        return [terminal, "--"] + shell
    if base == "xfce4-terminal":
        return [terminal, "-x"] + shell
    return [terminal, "-e"] + shell


def launch_login(command, on_exit, popen=subprocess.Popen, which=shutil.which, env=os.environ):
    terminal = find_terminal(which, env)
    if terminal is None:
        raise NoTerminal("no terminal emulator found")
    argv = build_login_argv(terminal, command)
    proc = popen(argv)

    def wait():
        try:
            proc.wait()
        finally:
            on_exit()

    threading.Thread(target=wait, daemon=True).start()
    return proc
