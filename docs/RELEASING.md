# Releasing

One-time setup:

1. Generate a dedicated signing key and export it:
   `gpg --quick-generate-key 'claude-monitoring apt <email>' rsa4096 sign 3y`, then
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
`src/claude_monitoring/__init__.py`, commit, then:

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
  `claude-monitoring_all.deb` and `SHA256SUMS` (only for signed tag builds).
- Older versions stay available because earlier release .debs are re-downloaded
  on each run.

## Images

`scripts/render-readme-images.py` regenerates the README images, the app logo
(`packaging/claude-monitoring.svg`) and `docs/img/social-preview.svg` from the
tray icon code. After changing the social preview, re-export it to PNG at
1280x640 and upload it under Settings > General > Social preview.
