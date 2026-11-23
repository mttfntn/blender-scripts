"""Compare two result files written by run_tests.py --json.

Usage: python tests/compare.py before.json after.json

Prints every case whose result differs and exits with code 1 if any do.
Use it to show that a refactor didn't change what the scripts produce.
"""

import json
import sys


def flatten(data, prefix=""):
    """Turn nested dicts into {"script/case": value} pairs."""
    if isinstance(data, dict):
        out = {}
        for key, value in data.items():
            out.update(flatten(value, f"{prefix}{key}/"))
        return out
    return {prefix.rstrip("/"): data}


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        before = flatten(json.load(f))
    with open(sys.argv[2], encoding="utf-8") as f:
        after = flatten(json.load(f))
    differences = 0
    for key in sorted(before.keys() | after.keys()):
        if before.get(key) != after.get(key):
            differences += 1
            print(f"DIFF {key}: {before.get(key)!r} -> {after.get(key)!r}")
    print(f"{len(before.keys() | after.keys())} cases compared, {differences} difference(s)")
    sys.exit(1 if differences else 0)


if __name__ == "__main__":
    main()
