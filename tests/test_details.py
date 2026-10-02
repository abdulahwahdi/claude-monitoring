import unittest
from datetime import datetime, timedelta, timezone

from claude_usage_linux import details
from claude_usage_linux.usage import UsageWindow

try:
    import cairo
except ImportError:
    cairo = None

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)


class DetailsTests(unittest.TestCase):
    def test_ease_out(self):
        self.assertEqual(details.ease_out(0), 0)
        self.assertEqual(details.ease_out(1), 1)
        self.assertEqual(details.ease_out(2), 1)
        self.assertGreater(details.ease_out(0.5), 0.5)

    def test_reset_at(self):
        local_now = NOW.astimezone()
        later = local_now.replace(hour=23, minute=59) if local_now.hour < 23 else local_now
        self.assertTrue(details.reset_at(later, NOW).startswith("today "))
        self.assertNotIn("today", details.reset_at(NOW + timedelta(days=3), NOW))

    @unittest.skipIf(cairo is None, "needs pycairo")
    def test_draw_all_states(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, details.WIDTH, details.HEIGHT)
        cr = cairo.Context(surface)
        windows = [("5-hour", UsageWindow(42, NOW + timedelta(hours=2))),
                   ("Weekly", UsageWindow(None))]
        details.draw(cr, details.WIDTH, details.HEIGHT, windows, [21, 0], None, NOW)
        details.draw(cr, details.WIDTH, details.HEIGHT, windows, [0, 0], "Offline", NOW)
