# Project Meridian 1.1 updates

Windows users migrating from 1.0.2 must download the new EXE once. Game data remains in the same ProjectMeridianLauncher directory. Later launcher releases are installed by clicking the update link in the header; a verified helper waits for the old process, backs up the EXE, replaces it, and restarts it. Protected installation folders may require moving the launcher to a writable folder.

Pack updates compare the installed files against a SHA-256-pinned file index. Only compressed ZIP member ranges for missing/changed files are fetched. GitHub must return exact HTTP 206 ranges: the updater never silently downloads the full ZIP when a range is ignored. First installation and legacy DEV migration still use the verified full ZIP.

All changed payloads are verified before replacement. A durable journal and backups allow rollback of failed file application and recovery after interruption. Only previously managed obsolete files are removed; unknown mods and preserved saves/options/voice settings remain. Repair uses the same selective mechanism.

## Publishing

The release workflow tests the Python code, publishes a backwards-compatible ZIP and its index, verifies live HTTP ranges, builds the Windows EXE, tests its UI and actual frozen self-update helper, then updates the public manifest. The launcher minimum remains 1.0.2 so existing users are not locked out.

Increment APP_VERSION and Windows version_info for every executable release. Versioned launcher URLs must be immutable. launcher-current is only a convenience link for manual downloads.

Every subsequent pack release MUST generate a new index with incremental.build_index(archive, immutable_package_url), upload it alongside the ZIP, and publish package + packVersion + fileIndex together. fileIndex contains url, sha256, size of the index JSON. Never leave an index from the previous ZIP in the manifest: mismatched indices are deliberately rejected. Existing pack-producing workflows need this step when next used. Do not overwrite previously published ZIP bytes.

The packaging script adds pinned Zume 1.2.2 once and verifies its Modrinth SHA-512. This is a client-only mod compatible with NeoForge 1.21.1; the server package does not need changes.

## Verification

- python launcher/tests/test_public_launcher.py (offline by default; optional --online-skins)
- python launcher/tests/test_incremental.py
- python launcher/tests/test_self_update.py
- Windows CI additionally runs source/frozen --smoke-ui and test_frozen_self_update.ps1.
- Actual current-pack migration fixture: 1,499 managed files verified, exactly one new compressed payload (91,344 bytes) for Zume, personal options unchanged. Index metadata is downloaded separately.

Minecraft gameplay needs validation on a player's Windows PC; CI validates the updater and launcher, not a live multiplayer session.
