import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from claude_usage_linux import icon

NS = "{http://www.w3.org/2000/svg}"


def circles(path):
    root = ET.parse(path).getroot()
    return root, root.findall(NS + "circle")


class IconTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name

    def test_creates_valid_svg(self):
        p = icon.render_icon(42, 17, "ok", self.dir)
        self.assertEqual(os.path.basename(p), "icon-42-17.svg")
        root, c = circles(p)
        self.assertEqual(len(c), 4)
        self.assertEqual(root.find(NS + "text").text, "42")

    def test_independent_colours(self):
        _, c = circles(icon.render_icon(95, 10, "ok", self.dir))
        arcs = [x for x in c if x.get("stroke-dasharray")]
        self.assertEqual(arcs[0].get("stroke"), icon.COLORS["crit"])
        self.assertEqual(arcs[1].get("stroke"), icon.COLORS["ok"])
        _, c = circles(icon.render_icon(75, 95, "ok", self.dir))
        arcs = [x for x in c if x.get("stroke-dasharray")]
        self.assertEqual(arcs[0].get("stroke"), icon.COLORS["warn"])
        self.assertEqual(arcs[1].get("stroke"), icon.COLORS["crit"])

    def test_unknown_window_only_track(self):
        root, c = circles(icon.render_icon(50, None, "ok", self.dir))
        self.assertEqual(len(c), 3)
        root, c = circles(icon.render_icon(None, 50, "ok", self.dir))
        self.assertEqual(len(c), 3)
        self.assertEqual(root.find(NS + "text").text, "!")

    def test_error_state(self):
        p = icon.render_icon(None, None, "error", self.dir)
        self.assertEqual(os.path.basename(p), "icon-error.svg")
        root, c = circles(p)
        self.assertEqual(len(c), 2)
        self.assertEqual(root.find(NS + "text").text, "!")

    def test_cleanup(self):
        icon.render_icon(1, 2, "ok", self.dir)
        icon.render_icon(3, 4, "ok", self.dir)
        self.assertEqual(sorted(os.listdir(self.dir)), ["icon-3-4.svg"])


if __name__ == "__main__":
    unittest.main()


class RingTests(unittest.TestCase):
    def test_ring_colour_follows_severity(self):
        self.assertIn(icon.COLORS["ok"], icon.build_ring_svg(42))
        self.assertIn(icon.COLORS["crit"], icon.build_ring_svg(95))
        ET.fromstring(icon.build_ring_svg(None))

    def test_render_ring_keeps_one_file_per_slot(self):
        with tempfile.TemporaryDirectory() as d:
            icon.render_ring(0, 10, d)
            icon.render_ring(1, 20, d)
            path = icon.render_ring(0, 30, d)
            self.assertEqual(sorted(os.listdir(d)), ["ring-0-30.svg", "ring-1-20.svg"])
            self.assertTrue(path.endswith("ring-0-30.svg"))
