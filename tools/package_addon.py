#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import zipfile
from pathlib import Path


IGNORE_DIRS = {
    ".git",
    ".github",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "tools",
}

IGNORE_SUFFIXES = {
    ".pyc",
    ".pyo",
}

IGNORE_FILES = {
    "requirements.txt",
}


def update_version(addon_dir: Path, version: str) -> None:
    toc = addon_dir / "AltertimeAddon.toc"
    core = addon_dir / "Core.lua"

    if toc.exists():
        toc_text = toc.read_text(encoding="utf-8")
        toc_text = re.sub(
            r"^## Version: .*$",
            f"## Version: {version}",
            toc_text,
            flags=re.M,
        )
        toc.write_text(toc_text, encoding="utf-8", newline="\n")

    if core.exists():
        core_text = core.read_text(encoding="utf-8")
        core_text = re.sub(
            r'ns\.VERSION = "[^"]+"',
            f'ns.VERSION = "{version}"',
            core_text,
        )
        core.write_text(core_text, encoding="utf-8", newline="\n")


def should_include(path: Path) -> bool:
    if any(part in IGNORE_DIRS for part in path.parts):
        return False

    if path.name in IGNORE_FILES:
        return False

    if path.suffix.lower() in IGNORE_SUFFIXES:
        return False

    if "_raw" in path.parts:
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--addon-dir", default=".")
    parser.add_argument("--folder-name", default="AltertimeAddon")
    parser.add_argument("--version", default=os.environ.get("ADDON_VERSION", "0.3.1-alpha"))
    parser.add_argument("--out-dir", default="dist")
    parser.add_argument("--no-version-update", action="store_true")
    args = parser.parse_args()

    addon_dir = Path(args.addon_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not addon_dir.exists():
        raise SystemExit(f"No existe addon-dir: {addon_dir}")

    if not args.no_version_update:
        update_version(addon_dir, args.version)

    zip_path = out_dir / f"AltertimeAddon-{args.version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in addon_dir.rglob("*"):
            if not file.is_file():
                continue

            rel_inside = file.relative_to(addon_dir)

            if not should_include(rel_inside):
                continue

            rel_zip = Path(args.folder_name) / rel_inside
            z.write(file, rel_zip)

    print(f"ZIP generado: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
