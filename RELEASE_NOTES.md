# Plotter v0.2.0-alpha

## Overview
This release establishes a repeatable build and prerelease workflow for Plotter while preparing the project for future alpha drops.

## Highlights
- Enforced version naming rule: `MAJOR.MINOR.PATCH-alpha` (example: `0.2.0-alpha`).
- Version-aware PyInstaller output naming through `main.spec`.
- Local one-command release build via `scripts/release.ps1`.
- Automated GitHub prerelease creation from version tags.

## Build and Release Rule
- App version source of truth is `__version__` in `main.py`.
- Git tag must be `v<version>` (for example `v0.2.0-alpha`).
- `CHANGELOG.md` and `RELEASE_NOTES.md` must include the same version.

## Quick Start (Local)
```powershell
./scripts/release.ps1
```

## Quick Start (GitHub)
1. Commit your release files.
2. Create and push a tag:
   ```bash
   git tag v0.2.0-alpha
   git push origin v0.2.0-alpha
   ```
3. GitHub Actions builds and publishes a prerelease automatically.

## Known Limitations
- Project save/load and advanced plotting roadmap items remain in progress.
- See TODO.md for ongoing development items.
