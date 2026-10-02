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

## Install with apt (Debian/Ubuntu/Mint)

Recommended on Debian-based systems. There is no hosted apt repository yet, so
build the package from a checkout:

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

## Troubleshooting

- *No icon:* on GNOME install the AppIndicator extension; elsewhere check the panel
  has a status notifier / system tray applet.
- *Startup error about typelibs:* install the dependencies above.
- *"No terminal found":* run `claude auth login` yourself, or set `TERMINAL`.
- *"Offline":* the API could not be reached; it keeps retrying.
