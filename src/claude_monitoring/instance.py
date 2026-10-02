"""Single-instance lock. No GTK here.

The first instance holds an flock on a per-user lock file holding its PID.
A second launch signals that PID (SIGUSR1, which opens the usage window)
and exits instead of adding another icon to the panel.
"""

import fcntl
import os
import signal
from typing import Optional

LOCK_NAME = "instance.lock"


def acquire(directory) -> Optional[int]:
    """Return the locked fd, or None if another instance holds the lock.

    The fd is not inheritable, so the lock is released on exec/exit.
    """
    path = os.path.join(directory, LOCK_NAME)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


def running_pid(directory) -> Optional[int]:
    try:
        with open(os.path.join(directory, LOCK_NAME), "r", encoding="ascii") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def notify_running(directory, kill=os.kill) -> bool:
    """Ask the running instance to show its window. True if it was signalled."""
    pid = running_pid(directory)
    if pid is None:
        return False
    try:
        kill(pid, signal.SIGUSR1)
    except OSError:
        return False
    return True
