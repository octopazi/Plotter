import argparse
import pathlib
import re
import sys

VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-alpha$")
VERSION_LINE_RE = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)


def read_project_version(main_py: pathlib.Path) -> str:
    text = main_py.read_text(encoding="utf-8")
    match = VERSION_LINE_RE.search(text)
    if not match:
        raise ValueError(f"Could not find __version__ in {main_py}")
    return match.group(1)


def ensure_version_format(version: str) -> None:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(
            "Invalid version format. Expected MAJOR.MINOR.PATCH-alpha (for example: 0.2.0-alpha)."
        )


def ensure_contains(path: pathlib.Path, token: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if token not in text:
        raise ValueError(f"{label} does not contain required token: {token}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Plotter release version rules.")
    parser.add_argument("--main-file", default="main.py", help="Path to main.py containing __version__")
    parser.add_argument("--expected", help="Expected version string (for example from git tag without leading v)")
    parser.add_argument("--print-version", action="store_true", help="Print discovered version and exit")
    parser.add_argument("--changelog", help="Path to CHANGELOG.md for heading check")
    parser.add_argument("--release-notes", help="Path to RELEASE_NOTES.md for heading check")
    args = parser.parse_args()

    main_py = pathlib.Path(args.main_file)
    version = read_project_version(main_py)
    ensure_version_format(version)

    if args.expected and version != args.expected:
        raise ValueError(f"Version mismatch: main.py has '{version}', expected '{args.expected}'")

    if args.changelog:
        ensure_contains(pathlib.Path(args.changelog), f"[v{version}]", "CHANGELOG")

    if args.release_notes:
        ensure_contains(pathlib.Path(args.release_notes), f"Plotter v{version}", "RELEASE_NOTES")

    if args.print_version:
        print(version)
    else:
        print(f"Version OK: {version}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Version validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
