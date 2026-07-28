#!/usr/bin/env python3
"""Print a detailed layer-size breakdown for a Docker image.

Runs `docker history` on an already-pulled image, sorts layers by size
(descending), and renders a markdown table with each layer's share of the
total image size. Writes to stdout and, if set, appends to
$GITHUB_STEP_SUMMARY so the breakdown shows up directly in the Actions run
summary instead of being buried in step logs.

Usage: analyze_image_layers.py IMAGE_REF
"""
import os
import re
import subprocess
import sys

UNITS = {"B": 1, "kB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}

# CreatedBy strings for base-image layers we didn't author are often just
# noise (long buildkit-internal commands); keep the full command but cap
# how much of it we render so the table stays readable.
MAX_CMD_LEN = 200


def parse_size(size_str: str) -> float:
    size_str = size_str.strip()
    if size_str in ("0B", ""):
        return 0.0
    m = re.match(r"([\d.]+)\s*([kKMGT]?B)", size_str)
    if not m:
        return 0.0
    value, unit = m.groups()
    return float(value) * UNITS.get(unit, 1)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: analyze_image_layers.py IMAGE_REF", file=sys.stderr)
        return 1
    image_ref = sys.argv[1]

    result = subprocess.run(
        [
            "docker",
            "history",
            "--no-trunc",
            "--format",
            "{{.Size}}||{{.CreatedBy}}",
            image_ref,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"docker history failed for {image_ref}:\n{result.stderr}", file=sys.stderr)
        return result.returncode

    rows = []
    total = 0.0
    for line in result.stdout.splitlines():
        if "||" not in line:
            continue
        size_s, cmd = line.split("||", 1)
        size = parse_size(size_s)
        total += size
        rows.append((size, size_s.strip(), cmd.strip()))
    rows.sort(key=lambda r: -r[0])

    lines = [
        f"### Layer size analysis: `{image_ref}`",
        "",
        f"**Total image size: {total / 1e9:.2f} GB** across {len(rows)} layers",
        "",
        "| Size | % of total | Command |",
        "|---:|---:|---|",
    ]
    for size, size_s, cmd in rows:
        pct = (size / total * 100) if total else 0
        cmd_md = cmd.replace("|", "\\|")
        if len(cmd_md) > MAX_CMD_LEN:
            cmd_md = cmd_md[:MAX_CMD_LEN] + "\u2026"
        lines.append(f"| {size_s} | {pct:.1f}% | `{cmd_md}` |")

    report = "\n".join(lines)
    try:
        print(report)
    except BrokenPipeError:
        pass

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as fh:
            fh.write(report + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
