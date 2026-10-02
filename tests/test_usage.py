import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone

from claude_monitoring import usage as u

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def write_creds(obj):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(obj, fh)
    fh.close()
    return fh.name


class FakeResp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TokenTests(unittest.TestCase):
    def test_ok(self):
        p = write_creds({"claudeAiOauth": {"accessToken": "tok", "expiresAt": (NOW.timestamp() + 100) * 1000}})
        self.addCleanup(os.remove, p)
        self.assertEqual(u.load_token(p, now=NOW.timestamp()), "tok")

    def test_expired(self):
        p = write_creds({"claudeAiOauth": {"accessToken": "tok", "expiresAt": (NOW.timestamp() - 1) * 1000}})
        self.addCleanup(os.remove, p)
        with self.assertRaises(u.TokenExpired):
            u.load_token(p, now=NOW.timestamp())

    def test_missing_file(self):
        with self.assertRaises(u.NoCredentials):
            u.load_token("/nonexistent/creds.json")

    def test_missing_token(self):
        p = write_creds({"claudeAiOauth": {}})
        self.addCleanup(os.remove, p)
        with self.assertRaises(u.NoCredentials):
            u.load_token(p)

    def test_env_override(self):
        p = write_creds({"claudeAiOauth": {"accessToken": "envtok"}})
        self.addCleanup(os.remove, p)
        old = os.environ.get("CLAUDE_USAGE_CREDENTIALS")
        os.environ["CLAUDE_USAGE_CREDENTIALS"] = p
        try:
            self.assertEqual(u.load_token(), "envtok")
        finally:
            if old is None:
                del os.environ["CLAUDE_USAGE_CREDENTIALS"]
            else:
                os.environ["CLAUDE_USAGE_CREDENTIALS"] = old

    def test_bad_json(self):
        fh = tempfile.NamedTemporaryFile("w", delete=False)
        fh.write("{nope")
        fh.close()
        self.addCleanup(os.remove, fh.name)
        with self.assertRaises(u.BadCredentials):
            u.load_token(fh.name)


class ParseTests(unittest.TestCase):
    def test_full(self):
        d = u.parse_usage({"five_hour": {"utilization": 42.5, "resets_at": "2026-01-01T14:10:00Z"},
                           "seven_day": {"utilization": 17, "resets_at": None}})
        self.assertEqual(d.five_hour.percent, 42.5)
        self.assertEqual(d.five_hour.resets_at, datetime(2026, 1, 1, 14, 10, tzinfo=timezone.utc))
        self.assertIsNone(d.weekly.resets_at)

    def test_nulls_and_missing(self):
        d = u.parse_usage({"five_hour": {"utilization": None}})
        self.assertIsNone(d.five_hour.percent)
        self.assertIsNone(d.weekly.percent)
        self.assertIsNone(u.parse_usage(None).five_hour.percent)

    def test_garbage_time(self):
        d = u.parse_usage({"five_hour": {"utilization": 1, "resets_at": "xx"}})
        self.assertIsNone(d.five_hour.resets_at)


class FormatTests(unittest.TestCase):
    def test_reset(self):
        self.assertEqual(u.format_reset(NOW + timedelta(hours=2, minutes=10), NOW), "2h 10m")
        self.assertEqual(u.format_reset(NOW + timedelta(days=3, hours=4, minutes=5), NOW), "3d 4h")
        self.assertEqual(u.format_reset(NOW + timedelta(minutes=5), NOW), "5m")
        self.assertEqual(u.format_reset(NOW, NOW), "now")
        self.assertEqual(u.format_reset(NOW - timedelta(hours=1), NOW), "now")

    def test_severity(self):
        self.assertEqual(u.severity(0), "ok")
        self.assertEqual(u.severity(69.9), "ok")
        self.assertEqual(u.severity(70), "warn")
        self.assertEqual(u.severity(89), "warn")
        self.assertEqual(u.severity(90), "crit")
        self.assertEqual(u.severity(None), "unknown")

    def test_menu_lines(self):
        w = lambda p: u.UsageWindow(p, NOW + timedelta(hours=2, minutes=10))
        l1, l2 = u.menu_lines("5-hour", w(42), NOW)
        self.assertEqual(l1, "5-hour   42%  ·  On track")
        self.assertTrue(l2.startswith("Resets in 2h 10m  ·  "))
        self.assertIn("Running high", u.menu_lines("5-hour", w(75), NOW)[0])
        self.assertIn("Almost out", u.menu_lines("5-hour", w(95), NOW)[0])
        self.assertEqual(u.menu_lines("Weekly", u.UsageWindow(), NOW), ("Weekly   n/a", ""))
        self.assertEqual(u.menu_lines("Weekly", u.UsageWindow(10), NOW)[1], "")


class FetchTests(unittest.TestCase):
    def test_success_and_headers(self):
        seen = {}

        def opener(req, timeout):
            seen["req"], seen["timeout"] = req, timeout
            return FakeResp(b'{"five_hour": {"utilization": 1}}')

        self.assertEqual(u.fetch_usage("tok", opener)["five_hour"]["utilization"], 1)
        self.assertEqual(seen["req"].get_header("Authorization"), "Bearer tok")
        self.assertEqual(seen["req"].get_header("Anthropic-beta"), "oauth-2025-04-20")
        self.assertEqual(seen["timeout"], 10)

    def _raiser(self, exc):
        def opener(req, timeout):
            raise exc
        return opener

    def test_errors(self):
        http = lambda c: urllib.error.HTTPError("x", c, "m", {}, None)
        with self.assertRaises(u.AuthError):
            u.fetch_usage("t", self._raiser(http(401)))
        with self.assertRaises(u.RateLimited):
            u.fetch_usage("t", self._raiser(http(429)))
        with self.assertRaises(u.Offline):
            u.fetch_usage("t", self._raiser(urllib.error.URLError("down")))


class NeedsLoginTests(unittest.TestCase):
    def test_table(self):
        for cls in (u.NoCredentials, u.TokenExpired, u.AuthError, u.BadCredentials):
            self.assertTrue(u.needs_login(cls("x")))
        for exc in (u.Offline("x"), u.RateLimited("x"), ValueError(), None):
            self.assertFalse(u.needs_login(exc))


if __name__ == "__main__":
    unittest.main()
