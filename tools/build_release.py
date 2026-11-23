# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the release zip: dist/blender-scripts-vX.Y.Z.zip.

Usage (from the repository root, plain Python 3, no Blender needed):

    python tools/build_release.py [--tag vX.Y.Z] [--badge-json PATH]

The zip holds scripts/*.py, LICENSE and README.md inside a blender-scripts/
folder. HANDOVER.md, AGENTS.md, tests and CI files are left out on purpose.
--tag fails the build unless it equals "v" + the version in manifest.json.
--badge-json writes a shields.io endpoint file with the zip's size.
"""

import argparse
import glob
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def package_files():
    """Paths (relative to the repo root) that go into the zip, sorted."""
    scripts = sorted(os.path.relpath(p, ROOT).replace(os.sep, "/")
                     for p in glob.glob(os.path.join(ROOT, "scripts", "*.py")))
    return scripts + ["LICENSE", "README.md"]


def human_size(size):
    return f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    parser.add_argument("--badge-json")
    args = parser.parse_args()

    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    name, version = manifest["name"], manifest["version"]
    if args.tag is not None and args.tag != f"v{version}":
        sys.exit(f"Tag {args.tag} does not match manifest.json version v{version}")

    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    zip_path = os.path.join(ROOT, "dist", f"{name}-v{version}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in package_files():
            # Fixed timestamp so the same sources always give the same zip.
            info = zipfile.ZipInfo(f"{name}/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(ROOT, rel), "rb") as f:
                zf.writestr(info, f.read())

    size = os.path.getsize(zip_path)
    print(f"{zip_path} ({human_size(size)})")
    if args.badge_json:
        with open(args.badge_json, "w", encoding="utf-8") as f:
            json.dump({"schemaVersion": 1, "label": "download", "message": human_size(size),
                       "color": "blue"}, f)


if __name__ == "__main__":
    main()
