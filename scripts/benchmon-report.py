#!/usr/bin/env python3
"""Write an HTML BenchMon profile report for Cursor HTML Preview Pro.

HTML Preview Pro (george-alisson.html-preview-vscode) loads the active editor
via ``iframe.srcdoc`` under a parent CSP of ``default-src 'none'``. That blocks
every ``<img>`` load — relative paths *and* ``data:`` URIs.

The only figures that render are **inline SVG** (markup in the HTML itself).
This writer inlines BenchMon ``.svg`` outputs into ``REPORT.html``.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

MAX_PREVIEW_WIDTH = 1400
MAX_SAFE_PIXELS = 40_000_000
JPEG_QUALITY = "4"
# Keep REPORT.html usable inside Preview Pro's srcdoc JSON.stringify path.
MAX_INLINE_SVG_BYTES = 2_500_000


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as handle:
            if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
            length = handle.read(4)
            if handle.read(4) != b"IHDR":
                return None
            ihdr = handle.read(struct.unpack(">I", length)[0])
            return struct.unpack(">II", ihdr[:8])
    except Exception:
        return None


def figure_pngs(root: Path) -> list[Path]:
    """Return PNGs plus SVG-only figures emitted by BenchMon."""
    pngs = {
        path
        for path in root.rglob("*.png")
        if path.is_file() and "figures" not in path.parts
    }
    svg_only = {
        path
        for path in root.rglob("*.svg")
        if path.is_file()
        and "figures" not in path.parts
        and not path.with_suffix(".png").is_file()
    }
    return sorted(
        pngs | svg_only
    )


def sibling_svg(png: Path) -> Path | None:
    if png.suffix.lower() == ".svg":
        return png
    cand = png.with_suffix(".svg")
    return cand if cand.is_file() else None


def chunk_label(figure: Path, root: Path) -> str:
    for parent in figure.parents:
        name = parent.name
        if name.startswith("benchmon_traces_"):
            return name.removeprefix("benchmon_traces_")
        if parent == root:
            break
    return figure.parent.name


def slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")
    return text or "figure"


def make_jpeg_preview(src: Path, dest: Path) -> Path | None:
    """Still write JPEGs for external browsers / file viewers; not used by Preview Pro."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = png_size(src)
    pixels = (size[0] * size[1]) if size else None
    vf = f"scale={MAX_PREVIEW_WIDTH}:-1:flags=lanczos,format=yuv420p"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-vf",
                vf,
                "-q:v",
                JPEG_QUALITY,
                str(dest),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if dest.is_file() and dest.stat().st_size > 0:
            os.chmod(dest, 0o644)
            return dest
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    if pixels is not None and pixels > MAX_SAFE_PIXELS:
        return None
    try:
        from PIL import Image  # type: ignore

        Image.MAX_IMAGE_PIXELS = MAX_SAFE_PIXELS
        with Image.open(src) as image:
            image.load()
            if image.mode != "RGB":
                image = image.convert("RGB")
            width, _height = image.size
            if width > MAX_PREVIEW_WIDTH:
                scale = MAX_PREVIEW_WIDTH / float(width)
                image = image.resize(
                    (max(1, int(width * scale)), max(1, int(image.size[1] * scale))),
                    Image.Resampling.LANCZOS,
                )
            image.save(dest, format="JPEG", quality=85, optimize=True)
            os.chmod(dest, 0o644)
            return dest
    except Exception:
        return None


def sanitize_inline_svg(raw: str) -> str:
    """Strip XML prolog/DOCTYPE so the fragment is valid HTML5 inline SVG."""
    text = raw.lstrip("\ufeff")
    text = re.sub(r"<\?xml[^?]*\?>", "", text, count=1, flags=re.IGNORECASE)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, count=1, flags=re.IGNORECASE)
    # Drop RDF metadata blocks (optional; keeps HTML lighter).
    text = re.sub(
        r"<metadata\b[^>]*>.*?</metadata>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Ensure the root svg scales in the preview pane.
    text = re.sub(
        r"<svg\b([^>]*)>",
        lambda m: (
            m.group(0)
            if "max-width" in m.group(1)
            else f'<svg style="max-width:100%;height:auto;display:block;background:#fff"{m.group(1)}>'
        ),
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return text.strip()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(text)
        tmp_name = handle.name
    tmp = Path(tmp_name)
    tmp.chmod(0o644)
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output HTML path (REPORT.html). .md suffixes are coerced to .html.",
    )
    parser.add_argument("--title", type=str, default="BenchMon profile")
    parser.add_argument(
        "--include-detailed",
        action="store_true",
        help="Also inline detailed SVGs (larger; may slow HTML Preview Pro).",
    )
    args = parser.parse_args()

    root = args.profiles_root.resolve()
    output = args.output.resolve()
    if output.suffix.lower() != ".html":
        output = output.with_suffix(".html")

    figures_dir = output.parent / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(figures_dir, 0o755)
    except OSError:
        pass
    for child in list(figures_dir.iterdir()):
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except OSError:
            pass

    pngs = figure_pngs(root)
    chunks = sorted(
        {
            figure.parent
            for figure in pngs
            if figure.parent.name.startswith("benchmon_traces_")
        }
    )
    synchronized = [
        path
        for path in pngs
        if "multi-node" in path.name.lower() or "multi_node" in path.name.lower()
    ]

    sections: list[str] = []
    inlined = 0
    skipped_svg = 0

    def add_figure(png: Path, heading: str) -> None:
        nonlocal inlined, skipped_svg
        label = chunk_label(png, root)
        preview_name = f"{slug(label)}__{slug(png.stem)}.jpg"
        make_jpeg_preview(png, figures_dir / preview_name)
        size_mib = png.stat().st_size / (1024 * 1024)
        dims = png_size(png)
        dim_txt = f"{dims[0]}x{dims[1]}, " if dims else ""
        src_rel = png.relative_to(root).as_posix()
        svg = sibling_svg(png)

        sections.append(f"<section><h3>{html.escape(heading)}</h3>")
        sections.append("<ul>")
        sections.append(f"<li>Machine: <code>{html.escape(label)}</code></li>")
        sections.append(
            f"<li>Source: <code>{html.escape(src_rel)}</code> "
            f"({html.escape(dim_txt)}{size_mib:.1f} MiB)</li>"
        )
        if svg is not None:
            sections.append(
                f"<li>Inline SVG: <code>{html.escape(svg.relative_to(root).as_posix())}</code> "
                f"({svg.stat().st_size / 1024:.0f} KiB)</li>"
            )
        sections.append("</ul>")

        if svg is not None and svg.stat().st_size <= MAX_INLINE_SVG_BYTES:
            sections.append('<div class="plot">')
            sections.append(sanitize_inline_svg(svg.read_text(encoding="utf-8", errors="replace")))
            sections.append("</div>")
            inlined += 1
        elif svg is not None:
            skipped_svg += 1
            sections.append(
                f"<p>SVG too large to inline for Preview Pro "
                f"({svg.stat().st_size / 1024 / 1024:.1f} MiB &gt; "
                f"{MAX_INLINE_SVG_BYTES / 1024 / 1024:.1f} MiB limit). "
                f"Open <code>{html.escape(svg.relative_to(root).as_posix())}</code> "
                "directly in Cursor.</p>"
            )
        else:
            sections.append(
                "<p>No sibling <code>.svg</code> found — Preview Pro cannot show "
                f"<code>&lt;img&gt;</code> resources. PNG at "
                f"<code>{html.escape(src_rel)}</code>.</p>"
            )
        sections.append("</section>")

    sections.append(f"<h1>{html.escape(args.title)}</h1>")
    sections.append(f"<p>Profile root: <code>{html.escape(str(root))}</code></p>")
    sections.append(
        f"<p>Machine chunks collected: {len(chunks)} | "
        f"Source PNG figures: {len(pngs)}</p>"
    )
    sections.append(
        "<p><strong>Cursor HTML Preview Pro note:</strong> that extension "
        "renders via <code>iframe.srcdoc</code> with "
        "<code>default-src 'none'</code>, so images cannot load. "
        "Plots below are <em>inline SVG</em> (not <code>&lt;img&gt;</code>).</p>"
    )

    sections.append("<h2>Synchronized multi-machine plots</h2>")
    if synchronized:
        for figure in synchronized:
            add_figure(figure, figure.stem.replace("_", " "))
    else:
        sections.append(
            "<p>No synchronized plot was produced. BenchMon creates one when "
            "at least two machine chunks contain completed traces.</p>"
        )

    sections.append("<h2>Per-machine overview plots</h2>")
    # Default: overview only — HTML Preview Pro embeds the whole file via
    # JSON.stringify(srcdoc); multi-MiB detailed SVGs make that unusable.
    per_machine = [p for p in pngs if p not in synchronized]
    if not args.include_detailed:
        per_machine = [p for p in per_machine if "overview" in p.name]
        skipped_detail = sum(
            1 for p in pngs if p not in synchronized and "overview" not in p.name
        )
        if skipped_detail:
            sections.append(
                f"<p>Showing overview plots only ({skipped_detail} detailed "
                "figure(s) omitted for Preview Pro size). Re-run with "
                "<code>--include-detailed</code> for full plots.</p>"
            )
    ordered = sorted(per_machine, key=lambda p: str(p))
    for figure in ordered:
        label = chunk_label(figure, root)
        kind = figure.stem.replace("benchmon_figure_", "").replace("_", " ")
        add_figure(figure, f"{label} - {kind}")

    page = "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en"><head><meta charset="utf-8" />',
            f"<title>{html.escape(args.title)}</title>",
            "<style>",
            "body{font-family:ui-sans-serif,system-ui,sans-serif;margin:24px;max-width:1400px;line-height:1.45;color:#111;background:#fff}",
            "code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:0.92em}",
            "section{margin:1.5rem 0;padding-bottom:1rem;border-bottom:1px solid #eee}",
            "h1,h2,h3{line-height:1.2}",
            ".plot{overflow:auto;border:1px solid #ddd;padding:8px;background:#fff}",
            ".plot svg{max-width:100%;height:auto}",
            "</style></head><body>",
            *sections,
            "</body></html>",
            "",
        ]
    )
    atomic_write(output, page)

    stale_md = output.with_suffix(".md")
    if stale_md.exists():
        try:
            stale_md.unlink()
        except OSError:
            pass

    print(
        f"Wrote {output} ({output.stat().st_size / 1024 / 1024:.2f} MiB) "
        f"with {inlined} inline SVG plot(s) from {len(chunks)} chunks"
        + (f" (skipped {skipped_svg} oversized SVG)" if skipped_svg else "")
    )


if __name__ == "__main__":
    main()
