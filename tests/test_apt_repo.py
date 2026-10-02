import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://abdulahwahdi.github.io/claude-monitoring/"


class AptRepoTests(unittest.TestCase):
    def test_readme_urls_are_produced_by_build_script(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        script = (ROOT / "scripts" / "build-apt-repo.sh").read_text(encoding="utf-8")
        self.assertIn(BASE_URL + "claude-monitoring.gpg", readme)
        self.assertIn('URL="%s"' % BASE_URL, script)
        for name in ("Release", "Release.gpg", "InRelease", "Packages.gz", "claude-monitoring.gpg"):
            self.assertIn(name, script)

    def test_workflow_deploys_signed_tag_builds_to_pages(self):
        workflow = (ROOT / ".github" / "workflows" / "apt-repo.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"tags:\s*\['v\*'\]")
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("needs.build.outputs.signed == 'true'", workflow)


if __name__ == "__main__":
    unittest.main()
