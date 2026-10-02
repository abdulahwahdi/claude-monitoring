# claude-usage-linux

A tray indicator for Linux panels that shows your Claude usage next to the
wifi, sound and battery icons.

- **Icon:** two concentric rings. The outer ring is the 5-hour window, the thinner
  inner ring is the weekly window. Each ring has a faint track and its own colour:
  green below 70%, amber 70–89%, red from 90%. The 5-hour percentage is drawn in the
  centre. If something goes wrong the icon turns grey with a "!".
- **Menu:** click the icon to see text progress bars, a severity dot, the percentage
  and the reset time for both windows, plus `Refresh now` and `Quit`:

  ```
  🟢 5h      ▰▰▰▰▱▱▱▱▱▱  42%
        resets in 2h 10m
  🟢 Weekly  ▰▱▱▱▱▱▱▱▱▱  17%
        resets in 3d 4h
  ```

  Panels without an emoji font may show plain boxes instead of the severity dots.
- **Log in…:** shown only when you are not logged in (no credentials, expired token,
  or rejected token). It opens a terminal running the login command (default
  `claude auth login`) and refreshes when that terminal closes. The app never
  touches your token beyond reading it to query usage. It is hidden otherwise.

Works through StatusNotifierItem/AppIndicator: KDE, XFCE, Cinnamon, MATE, and GNOME
with the extension below. Python 3.9+, standard library only at runtime.

## Dependencies

- Debian/Ubuntu: `sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1`
- Fedora: `sudo dnf install python3-gobject libayatana-appindicator-gtk3`
- Arch: `sudo pacman -S python-gobject libayatana-appindicator`

GNOME needs the "AppIndicator and KStatusNotifierItem Support" extension.

## Install from the apt repository (Debian/Ubuntu/Mint)

Recommended on Debian-based systems. The repository is signed and hosted on
GitHub Pages:

```sh
sudo install -d -m 0755 /etc/apt/keyrings
sudo curl -fsSL https://abdulahwahdi.github.io/claude-usage-linux/claude-usage-linux.gpg -o /etc/apt/keyrings/claude-usage-linux.gpg
echo 'deb [signed-by=/etc/apt/keyrings/claude-usage-linux.gpg] https://abdulahwahdi.github.io/claude-usage-linux/ ./' | sudo tee /etc/apt/sources.list.d/claude-usage-linux.list
sudo apt update && sudo apt install claude-usage-linux
```

Updates arrive through `sudo apt update && sudo apt upgrade`. Downloading the
.deb directly or building it from source (next sections) remains available.

## Download the .deb (no build)

Download the latest release asset, verify it and install it with apt (which
resolves the dependencies):

```sh
curl -fsSLO https://github.com/abdulahwahdi/claude-usage-linux/releases/latest/download/claude-usage-linux_all.deb
curl -fsSLO https://github.com/abdulahwahdi/claude-usage-linux/releases/latest/download/SHA256SUMS
sha256sum -c --ignore-missing SHA256SUMS
sudo apt install ./claude-usage-linux_all.deb
```

Specific versions are on the
[Releases page](https://github.com/abdulahwahdi/claude-usage-linux/releases) as
`claude-usage-linux_<version>_all.deb`. A manually installed .deb does not
update itself; use the apt repository above for updates. To remove it:

```sh
sudo apt remove claude-usage-linux
```

## Build and install the .deb from source

Build the package from a checkout instead of using the repository:

```
sudo apt install devscripts debhelper dh-python pybuild-plugin-pyproject python3-setuptools
dpkg-buildpackage -us -uc -b
sudo apt install ../claude-usage-linux_*_all.deb
```

apt resolves and installs the GTK and AppIndicator dependencies. The autostart
entry is installed system-wide to `/etc/xdg/autostart`, so no manual copy is
needed. To remove it:

```
sudo apt remove claude-usage-linux
```

## Install with pip (other distros)

```
pip install --user .
```

In a virtualenv, create it with `--system-site-packages` so PyGObject is visible.
Then run `claude-usage-linux`.

### Autostart

The .deb already installs the autostart entry. For a pip install, copy it yourself:

```
mkdir -p ~/.config/autostart
cp packaging/claude-usage-linux.desktop ~/.config/autostart/
```

## Configuration

Environment variables or `~/.config/claude-usage-linux/config.json`
(env wins):

| Setting | Env | Default |
|---|---|---|
| `poll_interval_seconds` | `CLAUDE_USAGE_POLL_INTERVAL` | 120 (minimum 30) |
| `credentials_path` | `CLAUDE_USAGE_CREDENTIALS` | `~/.claude/.credentials.json` |
| `login_command` | `CLAUDE_USAGE_LOGIN_COMMAND` | `claude auth login` |

On HTTP 429 the poll interval doubles, up to 15 minutes, and resets on success.

## Caveats

Usage comes from an undocumented endpoint (`/api/oauth/usage`) using the OAuth token
Claude Code stores in `~/.claude/.credentials.json`. It may change or stop working
without notice; missing fields are shown as "n/a".

## Maintainer: publishing

One-time setup:

1. Generate a dedicated signing key and export it:
   `gpg --quick-generate-key 'claude-usage-linux apt <email>' rsa4096 sign 3y`, then
   `gpg --armor --export-secret-keys <KEYID>`.
2. Add the repository secret `APT_GPG_PRIVATE_KEY` (the armored private key) and,
   if the key has a passphrase, `APT_GPG_PASSPHRASE`. The workflow derives the key
   ID from the imported key, so no key-ID variable is needed.
3. Enable Settings > Pages > Source: GitHub Actions.
4. Allow tag deployments: Settings > Environments > `github-pages` > Deployment
   branches and tags, and add a rule for tag pattern `v*`. By default only the
   default branch may deploy, so without it a tag-triggered deploy fails with
   "Tag vX.Y.Z is not allowed to deploy to github-pages".

To release, bump `debian/changelog` (e.g. `dch -v X.Y.Z`) and `__version__` in
`src/claude_usage_linux/__init__.py`, commit, then:

```
git tag vX.Y.Z && git push origin vX.Y.Z
```

The tag must match the `debian/changelog` version or the workflow fails
(`tests/test_version.py` checks that the changelog and `__version__` agree).

If a tag was pushed before the bump, delete and re-create it on the fixed commit:

```
git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z
git tag vX.Y.Z && git push origin vX.Y.Z
```

Notes:

- Tag builds fail if `APT_GPG_PRIVATE_KEY` is missing; an unsigned repository is
  never published. A manual `workflow_dispatch` run without a key builds but does
  not deploy.
- Each tag release attaches the versioned .deb, a stable-name
  `claude-usage-linux_all.deb` and `SHA256SUMS` (only for signed tag builds).
- Older versions stay available because earlier release .debs are re-downloaded
  on each run.

## Troubleshooting

- *No icon:* on GNOME install the AppIndicator extension; elsewhere check the panel
  has a status notifier / system tray applet.
- *Startup error about typelibs:* install the dependencies above.
- *"No terminal found":* run `claude auth login` yourself, or set `TERMINAL`.
- *"Offline":* the API could not be reached; it keeps retrying.
