# Project Meridian Launcher 2.0

The launcher continues the existing 1.1.0 codebase. The public manifest remains on its current release until tested artifacts are published.

## Startup behavior

Minecraft runs under an independent, headless session monitor. Closing the launcher does not close the game's output pipe. Logs continue to be written with sign-in tokens masked.

The launcher closes after the current modpack reports its title screen (FancyMenu) or completed startup (ModernFix), followed by three seconds without a startup error or termination. The PortableMC `launched` event alone is insufficient. A nonzero Minecraft `terminated` code is reported even when PortableMC itself exits with code zero. Missing readiness confirmation leaves the launcher open.

Version 2.0.1 also follows the current instance's `logs/latest.log`: some mods stop forwarding startup messages to the console. The observer skips pre-existing entries and handles a newly created, replaced or truncated log. An old session's menu cannot confirm a new launch. Console messages wrapped by PortableMC as `_stdout_` retain their embedded render-thread information.

The UI receives progress and errors through its existing event queue. Errors keep the window open for diagnosis. If a failed Minecraft process still owns the instance, launch and repair remain locked until that process exits.

## Installation and self-update

Windows builds use PyInstaller `--onedir`. Distribute the EXE installer or the complete ZIP; copying only the executable does not include its dependencies.

The installer defaults to `%LOCALAPPDATA%\Programs\Project Meridian Launcher` and does not request elevation. Game data stays in the existing `%LOCALAPPDATA%\ProjectMeridianLauncher` directory. Installation into a directory containing `instance` or `state.json` is refused. Uninstalling the program does not remove the game directory.

The public `launcher.url` points to the installer, keeping the existing download URL shape compatible with the website and old launcher. New clients use `launcher.bundle` for self-update. All bundled files are checked before replacement, a copied helper includes its own runtime, the parent exits only after the helper acknowledges startup, and the new app passes a UI smoke check before restart. Replacement/startup failure restores the old program directory. A small independent bootstrap remains outside the updated `app` folder. It restores the previous complete bundle after a power interruption or killed updater; a named mutex prevents simultaneous recovery and update. The last backup is kept in `app.previous`. The installer supplies the stable bootstrap itself.

## Pack updates

The existing index, SHA-256 validation, user-file preservation and transaction recovery remain in use. Verified payloads survive interrupted updates. An unfinished compressed file now persists to `.range.part` and resumes at its saved offset; its identity includes the immutable pack digest and byte range. The remaining-space calculation accounts for reusable cached payloads and already saved bytes. Incorrect HTTP ranges are refused without silently downloading the full archive. Corrupt compressed data is discarded before retry, and the installed pack remains unchanged until all payloads are verified.

Launcher publication updates only the `launcher` field in the latest manifest. It preserves the latest pack, file index and minimum launcher version. It verifies the uploaded installer and bundle before publishing metadata, then refreshes the compatible download alias. It does not rebuild or republish the modpack. A separate pack release must publish an immutable ZIP and matching SHA-256-pinned file index together.

## Build and verification

Requirements: Windows x64, Python 3.12, Pillow, PyInstaller 6.22.3 and Inno Setup 6. The compiler can be supplied as a portable directory.

From the repository root:

```powershell
python -m pip install pyinstaller==6.22.3 'pillow>=10,<13'
python -m unittest discover -s launcher/tests -p 'test_*.py'
python launcher/tests/test_public_launcher.py
launcher/build/build_windows.ps1 -Compiler 'C:\path\to\ISCC.exe'
launcher/tests/test_frozen_self_update.ps1
launcher/tests/test_frozen_game_session.ps1
launcher/tests/test_update_recovery.ps1
launcher/tests/test_installer.ps1
```

Run the Windows test scripts in Windows PowerShell 5.1. The installer test refuses to overwrite an existing installation registration. `-SkipInstaller` builds only the complete ZIP. Build outputs and release metadata are under `dist/` and `.out/`; `SHA256SUMS.txt` describes the deliverables. `publish_manifest.py` is a publication step and requires already uploaded, verified release assets.
