#!/bin/sh
# Install claude-usage-linux on Debian/Ubuntu/Mint.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/abdulahwahdi/claude-usage-linux/main/install.sh | sh
#
# Adds the signed apt repository and installs the package, so updates arrive
# through apt upgrade. If the repository is not published yet, falls back to
# the latest release .deb (verified against SHA256SUMS), which does not update
# itself.
set -eu

URL="https://abdulahwahdi.github.io/claude-usage-linux/"
RELEASES="https://github.com/abdulahwahdi/claude-usage-linux/releases/latest/download/"
KEYRING=/etc/apt/keyrings/claude-usage-linux.gpg
LIST=/etc/apt/sources.list.d/claude-usage-linux.list

die() {
    echo "error: $*" >&2
    exit 1
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

    if curl -fsSL "${URL}claude-usage-linux.gpg" -o "$tmp/claude-usage-linux.gpg"; then
        echo "deb [signed-by=$KEYRING] $URL ./" > "$tmp/claude-usage-linux.list"
        $sudo install -d -m 0755 "$root$(dirname "$KEYRING")" "$root$(dirname "$LIST")"
        $sudo install -m 0644 "$tmp/claude-usage-linux.gpg" "$root$KEYRING"
        $sudo install -m 0644 "$tmp/claude-usage-linux.list" "$root$LIST"
        $sudo apt-get update
        $sudo apt-get install -y claude-usage-linux
        echo "Installed from the apt repository; update with: sudo apt update && sudo apt upgrade"
    else
        echo "apt repository not available; installing the latest release .deb instead" >&2
        cd "$tmp"
        curl -fsSLO "${RELEASES}claude-usage-linux_all.deb"
        curl -fsSLO "${RELEASES}SHA256SUMS"
        sha256sum -c --ignore-missing SHA256SUMS
        chmod 0755 "$tmp"
        $sudo apt-get install -y "$tmp/claude-usage-linux_all.deb"
        echo "Installed from the release .deb; it does not update itself, re-run this installer to update."
    fi
}

# Everything runs from main so a partially downloaded script does nothing.
main "$@"
