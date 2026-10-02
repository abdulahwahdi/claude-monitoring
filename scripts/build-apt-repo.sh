#!/bin/sh
# Build a flat apt repository from a directory of .deb files.
#
# Usage: build-apt-repo.sh <deb-dir> <out-dir>
#
# If APT_GPG_KEY_ID is set, Release is signed (Release.gpg, InRelease) and the
# public key is exported to claude-monitoring.gpg. APT_GPG_PASSPHRASE is
# optional. Without a key the repository is left unsigned.
set -eu

URL="https://abdulahwahdi.github.io/claude-monitoring/"
REPO="https://github.com/abdulahwahdi/claude-monitoring"

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <deb-dir> <out-dir>" >&2
    exit 2
fi

deb_dir=$1
out_dir=$2

set -- "$deb_dir"/*.deb
if [ ! -e "$1" ]; then
    echo "error: no .deb files found in $deb_dir" >&2
    exit 1
fi

mkdir -p "$out_dir"
cp "$@" "$out_dir"/
cd "$out_dir"

rm -f Packages Packages.gz Release Release.tmp Release.gpg InRelease claude-monitoring.gpg

if [ ! -e index.html ]; then
    cat > index.html <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>claude-monitoring apt repository</title>
</head>
<body>
<h1>claude-monitoring apt repository</h1>
<pre>
sudo install -d -m 0755 /etc/apt/keyrings
sudo curl -fsSL ${URL}claude-monitoring.gpg -o /etc/apt/keyrings/claude-monitoring.gpg
echo "deb [signed-by=/etc/apt/keyrings/claude-monitoring.gpg] ${URL} ./" | sudo tee /etc/apt/sources.list.d/claude-monitoring.list
sudo apt update &amp;&amp; sudo apt install claude-monitoring
</pre>
<p><a href="${REPO}">Source on GitHub</a></p>
</body>
</html>
HTML
fi

dpkg-scanpackages --multiversion . /dev/null > Packages
gzip -9 -c Packages > Packages.gz

apt-ftparchive \
    -o APT::FTPArchive::Release::Origin=claude-monitoring \
    -o APT::FTPArchive::Release::Label=claude-monitoring \
    -o APT::FTPArchive::Release::Suite=stable \
    -o APT::FTPArchive::Release::Codename=stable \
    -o APT::FTPArchive::Release::Architectures=all \
    release . > Release.tmp
mv Release.tmp Release

gpg_sign() {
    if [ -n "${APT_GPG_PASSPHRASE:-}" ]; then
        printf %s "$APT_GPG_PASSPHRASE" | gpg --batch --yes --pinentry-mode loopback \
            --passphrase-fd 0 --local-user "$APT_GPG_KEY_ID" "$@"
    else
        gpg --batch --yes --pinentry-mode loopback --local-user "$APT_GPG_KEY_ID" "$@"
    fi
}

if [ -n "${APT_GPG_KEY_ID:-}" ]; then
    gpg_sign -abs -o Release.gpg Release
    gpg_sign --clearsign -o InRelease Release
    gpg --batch --yes --export "$APT_GPG_KEY_ID" > claude-monitoring.gpg
    if [ ! -s claude-monitoring.gpg ]; then
        echo "error: exported public key is empty" >&2
        exit 1
    fi
else
    echo "warning: APT_GPG_KEY_ID not set; repository is unsigned and consumers would need [trusted=yes]" >&2
fi
