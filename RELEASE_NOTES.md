# Plotter v0.2.0-alpha

## Overview
This release expands the day-to-day import and plotting workflow while also formalizing how Plotter is built and published. Compared with `v0.1.0-alpha`, the main additions are better config authoring, smarter header detection, config-driven plotting, richer plot inspection, and a repeatable prerelease pipeline.

## Highlights
- Sample-based header detection now supports simple and expert modes, including regex-driven column name extraction.
- Config files can define plot figures that run automatically after import or on demand through `Run Config Plots`.
- Plot windows now include coordinate picking, pinned annotations, and draggable dual vertical cursors for inspection.
- Dataset review is improved with column statistics, column deletion from the table header menu, and full float precision in the data grid.
- Release packaging is now version-aware and validated end-to-end for local and GitHub prereleases.

## Workflow Improvements
- The config editor now supports inline editing for Y columns, conversion rules, and plot figure definitions.
- Closing an edited config warns about unsaved changes before discarding work.
- Plotter remembers the last selected import config, edit target, run-plot config, and import directory between sessions.
- Imports now warn when detected file columns do not match config expectations, instead of silently proceeding.

## Build and Release Rule
- App version source of truth is `__version__` in `main.py`.
- Git tag must be `v<version>` (for example `v0.2.0-alpha`).
- `CHANGELOG.md` and `RELEASE_NOTES.md` must include the same version.
- `scripts/validate_version.py` enforces the `MAJOR.MINOR.PATCH-alpha` prerelease format and version consistency.

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
- Auto-plot can open many windows for large multi-file imports, so bulk launches may still need manual confirmation.
- See TODO.md for ongoing development items.
