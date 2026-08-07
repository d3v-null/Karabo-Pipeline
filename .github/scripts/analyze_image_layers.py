#!/usr/bin/env python3
"""Print a useful size breakdown for a Docker image.

`docker history` alone is easy to misread for Spack images: symlink-heavy
COPY layers (e.g. /opt/view) look huge in tools that follow links (dive),
while the real bytes live under /opt/software. This script reports:

1. docker history layer sizes (actual layer diffs, symlinks not followed)
2. on-disk path sizes inside the image (du, no -L)
3. largest Spack package prefixes under /opt/software

Writes to stdout and, if set, appends to $GITHUB_STEP_SUMMARY.

Usage: analyze_image_layers.py IMAGE_REF
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

# docker history uses "165MB" / "14.5GB"; GNU du -h uses "568M" / "14G".
UNITS = {
    "B": 1,
    "kB": 1e3,
    "KB": 1e3,
    "K": 1e3,
    "MB": 1e6,
    "M": 1e6,
    "GB": 1e9,
    "G": 1e9,
    "TB": 1e12,
    "T": 1e12,
}
MAX_CMD_LEN = 200
TOP_N_LAYERS = 30
TOP_N_PACKAGES = 15
PATHS = (
    "/opt/software",
    "/opt/view",
    "/opt/._view",
    "/opt/spack",
    "/opt/spack_env",
    "/opt/conda",
    "/opt/ms-playwright",
)


def parse_size(size_str: str) -> float:
    size_str = size_str.strip()
    if size_str in ("0B", "0", ""):
        return 0.0
    m = re.match(r"([\d.]+)\s*([kKMGT]B?|B)\b", size_str, re.IGNORECASE)
    if not m:
        return 0.0
    value, unit = m.groups()
    return float(value) * UNITS.get(unit, UNITS.get(unit.upper(), 1))


def fmt_bytes(n: float) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f}GB"
    if n >= 1e6:
        return f"{n / 1e6:.0f}MB"
    if n >= 1e3:
        return f"{n / 1e3:.0f}kB"
    return f"{int(n)}B"


def docker_history_rows(image_ref: str) -> tuple[list[tuple[float, str, str]], float]:
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
        raise RuntimeError(
            f"docker history failed for {image_ref}:\n{result.stderr}"
        )

    rows: list[tuple[float, str, str]] = []
    total = 0.0
    for line in result.stdout.splitlines():
        if "||" not in line:
            continue
        size_s, cmd = line.split("||", 1)
        size = parse_size(size_s)
        total += size
        rows.append((size, size_s.strip(), cmd.strip()))
    rows.sort(key=lambda r: -r[0])
    return rows, total


def docker_du(image_ref: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (path_rows, package_rows) as (size_str, path) lists."""
    paths = " ".join(PATHS)
    script = f"""
set -e
echo '===PATHS==='
for p in {paths}; do
  if [ -e "$p" ]; then du -sh "$p"; fi
done
echo '===PACKAGES==='
if [ -d /opt/software ]; then
  # Spack install tree: /opt/software/<arch>/<name>-<ver>-<hash>
  find /opt/software -mindepth 2 -maxdepth 2 -type d -print0 2>/dev/null \
    | xargs -0 -r du -sh 2>/dev/null \
    | sort -hr \
    | head -n {TOP_N_PACKAGES}
fi
"""
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "bash",
            image_ref,
            "-lc",
            script,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker run du failed for {image_ref}:\n{result.stderr}"
        )

    path_rows: list[tuple[str, str]] = []
    pkg_rows: list[tuple[str, str]] = []
    section = None
    for line in result.stdout.splitlines():
        if line == "===PATHS===":
            section = "paths"
            continue
        if line == "===PACKAGES===":
            section = "packages"
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        size_s, path = parts
        if section == "paths":
            path_rows.append((size_s, path))
        elif section == "packages":
            pkg_rows.append((size_s, path))
    return path_rows, pkg_rows


def md_escape_cmd(cmd: str) -> str:
    cmd_md = cmd.replace("|", "\\|")
    if len(cmd_md) > MAX_CMD_LEN:
        cmd_md = cmd_md[:MAX_CMD_LEN] + "\u2026"
    return cmd_md


def build_report(
    image_ref: str,
    hist_rows: list[tuple[float, str, str]],
    hist_total: float,
    path_rows: list[tuple[str, str]],
    pkg_rows: list[tuple[str, str]],
) -> str:
    lines = [
        f"### Image size analysis: `{image_ref}`",
        "",
        f"**Total (sum of layer diffs): {hist_total / 1e9:.2f} GB** "
        f"across {len(hist_rows)} history entries",
        "",
        "Layer sizes below are from `docker history` (symlink targets are "
        "**not** counted). Tools like dive that follow symlinks will "
        "over-attribute `/opt/view` and `/opt/._view` and under-count "
        "`/opt/software`.",
        "",
        "#### On-disk paths (du, no symlink follow)",
        "",
        "| Size | Path |",
        "|---:|---|",
    ]
    path_total = 0.0
    for size_s, path in path_rows:
        path_total += parse_size(size_s)
        note = ""
        if path in ("/opt/view", "/opt/._view"):
            note = " (Spack view symlink forest; mostly metadata)"
        lines.append(f"| {size_s} | `{path}`{note} |")
    if path_rows:
        lines.append("")
        lines.append(f"Sum of listed paths: **{fmt_bytes(path_total)}**")

    if pkg_rows:
        lines.extend(
            [
                "",
                "#### Largest Spack prefixes under `/opt/software`",
                "",
                "| Size | Prefix |",
                "|---:|---|",
            ]
        )
        for size_s, path in pkg_rows:
            name = path.rstrip("/").split("/")[-1]
            lines.append(f"| {size_s} | `{name}` |")

    view_hist = sum(
        s
        for s, _, c in hist_rows
        if "COPY /opt/view " in c or "COPY /opt/._view " in c
    )
    software_hist = sum(
        s for s, _, c in hist_rows if "COPY /opt/software " in c
    )
    if view_hist and software_hist:
        lines.extend(
            [
                "",
                "#### Spack COPY note",
                "",
                f"- `COPY /opt/software` layer(s): **{fmt_bytes(software_hist)}** "
                "(real package payloads)",
                f"- `COPY /opt/view` + `COPY /opt/._view` layer(s): "
                f"**{fmt_bytes(view_hist)}** (duplicate symlink trees; "
                "`/opt/view` normally points at `/opt/._view/<hash>`)",
            ]
        )

    lines.extend(
        [
            "",
            f"#### Top {TOP_N_LAYERS} layers by `docker history` size",
            "",
            "| Size | % of total | Command |",
            "|---:|---:|---|",
        ]
    )
    for size, size_s, cmd in hist_rows[:TOP_N_LAYERS]:
        pct = (size / hist_total * 100) if hist_total else 0
        lines.append(f"| {size_s} | {pct:.1f}% | `{md_escape_cmd(cmd)}` |")
    omitted = len(hist_rows) - TOP_N_LAYERS
    if omitted > 0:
        lines.append("")
        lines.append(f"_…{omitted} smaller history entries omitted._")

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: analyze_image_layers.py IMAGE_REF", file=sys.stderr)
        return 1
    image_ref = sys.argv[1]

    try:
        hist_rows, hist_total = docker_history_rows(image_ref)
        path_rows, pkg_rows = docker_du(image_ref)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = build_report(image_ref, hist_rows, hist_total, path_rows, pkg_rows)
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
