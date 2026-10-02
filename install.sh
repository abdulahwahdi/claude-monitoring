#!/bin/sh
# Install claude-monitoring on Debian/Ubuntu/Mint.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/abdulahwahdi/claude-monitoring/main/install.sh | sh
#
# Adds the signed apt repository and installs the package, so updates arrive
# through apt upgrade. If the repository is not published yet, falls back to
# the latest release .deb (verified against SHA256SUMS), which does not update
# itself.
set -eu

URL="https://abdulahwahdi.github.io/claude-monitoring/"
RELEASES="https://github.com/abdulahwahdi/claude-monitoring/releases/latest/download/"
KEYRING=/etc/apt/keyrings/claude-monitoring.gpg
LIST=/etc/apt/sources.list.d/claude-monitoring.list
# Before 2.0.0 the project was called claude-usage-linux.
OLD_KEYRING=/etc/apt/keyrings/claude-usage-linux.gpg
OLD_LIST=/etc/apt/sources.list.d/claude-usage-linux.list

die() {
    echo "error: $*" >&2
    exit 1
}

# Start the app detached from this terminal so it keeps running after the
# terminal closes. Later logins start it through the autostart entry.
start() {
    [ -z "$root" ] && [ "$(id -u)" -ne 0 ] || return 0
    [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || return 0
    command -v claude-monitoring >/dev/null 2>&1 || return 0
    pgrep -u "$(id -u)" -f 'bin/claude-monitoring' >/dev/null 2>&1 && return 0
    setsid -f claude-monitoring >/dev/null 2>&1 </dev/null &&
        echo "Started; look for the icon in your panel."
}

# Drop the pre-2.0.0 apt source, whose URL no longer exists (apt update would
# fail on it), and stop the old app. The new package replaces the old one.
migrate() {
    if [ -e "$root$OLD_LIST" ] || [ -e "$root$OLD_KEYRING" ]; then
        echo "Migrating from claude-usage-linux"
        $sudo rm -f "$root$OLD_LIST" "$root$OLD_KEYRING"
    fi
    [ -z "$root" ] || return 0
    pkill -u "$(id -u)" -f 'bin/claude-usage-linux' >/dev/null 2>&1 || true
}

# Removing the old package keeps its /etc files, including an autostart entry
# for a command that no longer exists. Purging deletes them.
purge_old() {
    [ -z "$root" ] || return 0
    if dpkg-query -W -f='${Status}' claude-usage-linux 2>/dev/null | grep -q config-files; then
        $sudo dpkg --purge claude-usage-linux >/dev/null
    fi
}

main() {
    # INSTALL_ROOT prefixes the files written, for testing only.
    root=${INSTALL_ROOT:-}

    command -v apt-get >/dev/null 2>&1 || die "apt-get not found; this installer supports Debian/Ubuntu/Mint only"
    command -v curl >/dev/null 2>&1 || die "curl not found; install it with: sudo apt install curl"

    if [ "$(id -u)" -eq 0 ]; then
        sudo=
    elif command -v sudo >/dev/null 2>&1; then
        sudo=sudo
    else
        die "run as root or install sudo"
    fi

    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    migrate

    if curl -fsSL "${URL}claude-monitoring.gpg" -o "$tmp/claude-monitoring.gpg"; then
        echo "deb [signed-by=$KEYRING] $URL ./" > "$tmp/claude-monitoring.list"
        $sudo install -d -m 0755 "$root$(dirname "$KEYRING")" "$root$(dirname "$LIST")"
        $sudo install -m 0644 "$tmp/claude-monitoring.gpg" "$root$KEYRING"
        $sudo install -m 0644 "$tmp/claude-monitoring.list" "$root$LIST"
        $sudo apt-get update
        $sudo apt-get install -y claude-monitoring
        echo "Installed from the apt repository; update with: sudo apt update && sudo apt upgrade"
        purge_old
        start
    else
        echo "apt repository not available; installing the latest release .deb instead" >&2
        cd "$tmp"
        curl -fsSLO "${RELEASES}claude-monitoring_all.deb" && curl -fsSLO "${RELEASES}SHA256SUMS" ||
            die "no published release found; build from source instead: https://github.com/abdulahwahdi/claude-monitoring#from-source-any-distro"
        sha256sum -c --ignore-missing SHA256SUMS
        chmod 0755 "$tmp"
        $sudo apt-get install -y "$tmp/claude-monitoring_all.deb"
        echo "Installed from the release .deb; it does not update itself, re-run this installer to update."
        purge_old
        start
    fi
}

# Everything runs from main so a partially downloaded script does nothing.
main "$@"
