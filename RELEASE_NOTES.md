# Plotter v0.3.0-alpha

## Overview
This release focuses on performance and workflow depth for real analysis sessions. Compared with `v0.2.0-alpha`, the major updates are import-time downsampling, multi-dataset plotting/alignment, plugin-based dataset processing, and stronger import robustness.

## Highlights
- Import-time downsampling is now built in, with configurable timing (`before_conversions` or `after_conversions`) and three methods: Decimation, LTTB, and DWT.
- Plot windows now support multi-dataset management, including add/remove dataset controls in the same figure.
- Dataset alignment now supports auto cross-correlation offsets, manual adjustment, and interpolation fallback for mismatched sampling rates.
- Script plugins can be launched from `Script -> Dataset process` to generate derived datasets from trusted local Python scripts.
- Import post-processing can now hide mapped columns from plot selectors or delete columns after processing via config.

## Workflow Improvements
- Config editor now includes dedicated Plot Config and Downsampling tabs.
- Dataset cleanup is faster with multi-select delete support.
- FFT analysis flow is smoother with preferred dataset preselection and row-range input.
- Data import now handles more CSV/header edge cases (separator normalization, expert regex extraction, column mapping/index handling).
- Data viewer rendering and dtype handling were improved for large/float-heavy datasets.

## Build and Release Rule
- App version source of truth is `__version__` in `main.py`.
- Git tag must be `v<version>` (for example `v0.3.0-alpha`).
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
   git tag v0.3.0-alpha
   git push origin v0.3.0-alpha
   ```
3. GitHub Actions builds and publishes a prerelease automatically.

## Known Limitations
- Project save/load and broader advanced plotting roadmap items remain in progress.
- Plot setup dialog still initializes from a single dataset; cross-dataset axis selection is currently done after opening the plot window.
- See TODO.md for ongoing development items.
