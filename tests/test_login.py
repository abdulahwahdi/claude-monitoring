import threading
import unittest

from claude_usage_linux import login


class FakeProc:
    def wait(self):
        return 0


class LoginTests(unittest.TestCase):
    def test_find_terminal_order(self):
        which = lambda n: "/bin/" + n if n in ("konsole", "xterm") else None
        self.assertEqual(login.find_terminal(which, {}), "konsole")

    def test_find_terminal_env_first(self):
        which = lambda n: "/bin/" + n
        self.assertEqual(login.find_terminal(which, {"TERMINAL": "foot"}), "foot")

    def test_find_terminal_none(self):
        self.assertIsNone(login.find_terminal(lambda n: None, {}))

    def test_argv(self):
        cmd = "claude auth login"
        a = login.build_login_argv("gnome-terminal", cmd)
        self.assertEqual(a[:3], ["gnome-terminal", "--", "sh"])
        self.assertIn(cmd, a[-1])
        self.assertIn("Press Enter", a[-1])
        self.assertEqual(login.build_login_argv("konsole", cmd)[1], "-e")
        self.assertEqual(login.build_login_argv("xfce4-terminal", cmd)[1], "-x")
        self.assertEqual(login.build_login_argv("xterm", cmd)[:3], ["xterm", "-e", "sh"])

    def test_launch_calls_on_exit(self):
        done = threading.Event()
        argv = []

        def popen(a):
            argv.extend(a)
            return FakeProc()

        login.launch_login("x", done.set, popen=popen, which=lambda n: n if n == "xterm" else None, env={})
        self.assertTrue(done.wait(2))
        self.assertEqual(argv[0], "xterm")

    def test_launch_no_terminal(self):
        with self.assertRaises(login.NoTerminal):
            login.launch_login("x", lambda: None, popen=None, which=lambda n: None, env={})


if __name__ == "__main__":
    unittest.main()
