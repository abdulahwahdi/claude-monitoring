import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "install.sh"
ONE_LINER = (
    "curl -fsSL https://raw.githubusercontent.com/abdulahwahdi/claude-usage-linux/main/install.sh | sh"
)
DEB = b"fake deb\n"

# Stub curl: fails for the apt key when CURL_KEY_FAIL is set, otherwise writes
# fixed contents to the -o file or to the URL basename for -O.
CURL_STUB = """#!/bin/sh
out=
url=
remote=
for a in "$@"; do
    case "$prev" in -o) out=$a ;; esac
    case "$a" in -*O*) remote=1 ;; http*) url=$a ;; esac
    prev=$a
done
echo "curl $url" >> "$STUB_LOG"
case "$url" in
    *.gpg) [ -n "${CURL_KEY_FAIL:-}" ] && exit 22; printf KEY > "$out" ;;
    *.deb) printf 'fake deb\\n' > "${url##*/}" ;;
    *SHA256SUMS) printf '%s  claude-usage-linux_all.deb\\n' "$DEB_SHA" > SHA256SUMS ;;
esac
"""


@unittest.skipUnless(shutil.which("sh") and shutil.which("sha256sum"), "needs sh and sha256sum")
class InstallScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "log"
        self.log.touch()
        self.root = self.tmp / "root"
        self._stub("curl", CURL_STUB)
        self._stub("apt-get", '#!/bin/sh\necho "apt-get $*" >> "$STUB_LOG"\n')
        self._stub("id", "#!/bin/sh\necho 0\n")

    def _stub(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def _run(self, **env):
        full_env = dict(
            os.environ,
            PATH="%s:%s" % (self.bin, os.environ.get("PATH", "")),
            STUB_LOG=str(self.log),
            INSTALL_ROOT=str(self.root),
            DEB_SHA=hashlib.sha256(DEB).hexdigest(),
            **env,
        )
        # Piped through stdin, as in the documented one-liner.
        result = subprocess.run(
            ["sh"], input=SCRIPT.read_bytes(), env=full_env, capture_output=True, cwd=self.tmp
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return self.log.read_text().splitlines()

    def test_syntax(self):
        subprocess.run(["sh", "-n", str(SCRIPT)], check=True)

    def test_adds_signed_repository_and_installs(self):
        log = self._run()
        keyring = self.root / "etc/apt/keyrings/claude-usage-linux.gpg"
        listing = self.root / "etc/apt/sources.list.d/claude-usage-linux.list"
        self.assertEqual(keyring.read_text(), "KEY")
        self.assertEqual(
            listing.read_text(),
            "deb [signed-by=/etc/apt/keyrings/claude-usage-linux.gpg] "
            "https://abdulahwahdi.github.io/claude-usage-linux/ ./\n",
        )
        self.assertEqual(log[-2:], ["apt-get update", "apt-get install -y claude-usage-linux"])

    def test_falls_back_to_release_deb_when_repository_missing(self):
        log = self._run(CURL_KEY_FAIL="1")
        self.assertFalse((self.root / "etc").exists())
        self.assertIn(
            "curl https://github.com/abdulahwahdi/claude-usage-linux/releases/latest/download/SHA256SUMS",
            log,
        )
        self.assertRegex(log[-1], r"^apt-get install -y /.*/claude-usage-linux_all\.deb$")

    def test_fallback_rejects_checksum_mismatch(self):
        result = subprocess.run(
            ["sh", str(SCRIPT)],
            env=dict(
                os.environ,
                PATH="%s:%s" % (self.bin, os.environ.get("PATH", "")),
                STUB_LOG=str(self.log),
                INSTALL_ROOT=str(self.root),
                DEB_SHA="0" * 64,
                CURL_KEY_FAIL="1",
            ),
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("apt-get install", self.log.read_text())

    def test_readme_documents_one_liner(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(ONE_LINER, readme)
        self.assertIn(ONE_LINER, SCRIPT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
