import json
import os
import tempfile
import unittest

from claude_monitoring import config


class ConfigPathTests(unittest.TestCase):
    def _write(self, base, name, data):
        os.makedirs(os.path.join(base, name))
        with open(os.path.join(base, name, "config.json"), "w") as fh:
            json.dump(data, fh)

    def test_new_path_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(config.config_path({"XDG_CONFIG_HOME": d}),
                             os.path.join(d, "claude-monitoring", "config.json"))

    def test_falls_back_to_pre_rename_config(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "claude-usage-linux", {"poll_interval_seconds": 300})
            env = {"XDG_CONFIG_HOME": d}
            self.assertIn("claude-usage-linux", config.config_path(env))
            self.assertEqual(config.load_config(env=env).poll_interval_seconds, 300)

    def test_new_config_wins_over_old(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "claude-usage-linux", {"poll_interval_seconds": 300})
            self._write(d, "claude-monitoring", {"poll_interval_seconds": 60})
            self.assertEqual(config.load_config(env={"XDG_CONFIG_HOME": d}).poll_interval_seconds, 60)
