import os
import signal
import tempfile
import unittest

from claude_monitoring import instance, update


class InstanceTests(unittest.TestCase):
    def test_second_acquire_fails_until_released(self):
        with tempfile.TemporaryDirectory() as d:
            fd = instance.acquire(d)
            self.assertIsNotNone(fd)
            self.assertEqual(instance.running_pid(d), os.getpid())
            self.assertIsNone(instance.acquire(d))
            os.close(fd)
            fd = instance.acquire(d)
            self.assertIsNotNone(fd)
            os.close(fd)

    def test_lock_fd_not_inherited(self):
        with tempfile.TemporaryDirectory() as d:
            fd = instance.acquire(d)
            self.assertFalse(os.get_inheritable(fd))
            os.close(fd)

    def test_notify_running(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(instance.notify_running(d, kill=lambda *a: sent.append(a)))
            fd = instance.acquire(d)
            self.assertTrue(instance.notify_running(d, kill=lambda *a: sent.append(a)))
            os.close(fd)
        self.assertEqual(sent, [(os.getpid(), signal.SIGUSR1)])

    def test_notify_dead_pid(self):
        def dead(*_a):
            raise ProcessLookupError
        with tempfile.TemporaryDirectory() as d:
            fd = instance.acquire(d)
            self.assertFalse(instance.notify_running(d, kill=dead))
            os.close(fd)


class UpdateTests(unittest.TestCase):
    def test_installed_from_package(self):
        self.assertTrue(update.installed_from_package(
            "/usr/lib/python3/dist-packages/claude_monitoring/update.py"))
        self.assertFalse(update.installed_from_package(
            os.path.expanduser("~/.local/lib/python3.12/site-packages/claude_monitoring/update.py")))

    def test_update_command_uses_installer(self):
        self.assertIn("install.sh", update.UPDATE_COMMAND)
        self.assertTrue(update.UPDATE_COMMAND.endswith("| sh"))
