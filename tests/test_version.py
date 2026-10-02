import re
import unittest
from pathlib import Path

import claude_monitoring

CHANGELOG = Path(__file__).resolve().parent.parent / "debian" / "changelog"


class VersionTests(unittest.TestCase):
    def test_changelog_matches_package_version(self):
        first_line = CHANGELOG.read_text(encoding="utf-8").splitlines()[0]
        match = re.match(r"^claude-monitoring \(([^)]+)\)", first_line)
        self.assertIsNotNone(match, first_line)
        version = re.sub(r"-[^-]+$", "", match.group(1))
        self.assertEqual(version, claude_monitoring.__version__)


if __name__ == "__main__":
    unittest.main()
