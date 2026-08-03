"""Make marimo PDF export work in Kubernetes singleuser pods.

Two issues in this environment:
1. Chromium needs --no-sandbox (no CAP_SYS_ADMIN).
2. marimo calls nbconvert WebPDF from inside asyncio.run; nbconvert then does
   ThreadPoolExecutor(asyncio.run(...)), which deadlocks. Run WebPDF in a
   fresh subprocess instead.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def _patch_webpdf_exporter() -> None:
    try:
        from nbconvert.exporters.webpdf import WebPDFExporter
    except Exception:
        return

    _orig_init = WebPDFExporter.__init__

    def _init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            self.disable_sandbox = True
            self.allow_chromium_download = False
            args_list = list(getattr(self, "browser_args", []) or [])
            for flag in ("--no-sandbox", "--disable-dev-shm-usage"):
                if flag not in args_list:
                    args_list.append(flag)
            self.browser_args = args_list
        except Exception:
            pass

    WebPDFExporter.__init__ = _init  # type: ignore[method-assign]


def _render_webpdf_subprocess(notebook, include_inputs: bool):
    import nbformat

    with tempfile.TemporaryDirectory(prefix="swf8-webpdf-") as td:
        td_path = Path(td)
        ipynb_path = td_path / "notebook.ipynb"
        pdf_path = td_path / "notebook.pdf"
        script_path = td_path / "render_webpdf.py"
        ipynb_path.write_text(nbformat.writes(notebook), encoding="utf-8")
        script_path.write_text(
            "\n".join(
                [
                    "import nbformat",
                    "from nbconvert import WebPDFExporter",
                    f"nb = nbformat.read({str(ipynb_path)!r}, as_version=4)",
                    "ex = WebPDFExporter()",
                    f"ex.exclude_input = {not include_inputs!r}",
                    "ex.allow_chromium_download = False",
                    "ex.disable_sandbox = True",
                    'ex.browser_args = ["--no-sandbox", "--disable-dev-shm-usage"]',
                    "pdf, _ = ex.from_notebook_node(nb)",
                    f"open({str(pdf_path)!r}, \"wb\").write(pdf)",
                ]
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "WebPDF subprocess failed:\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        return pdf_path.read_bytes()


def _patch_marimo_renderer() -> None:
    try:
        from marimo._server.export import exporter as exp
    except Exception:
        return
    if getattr(exp, "_swf8_webpdf_subprocess", False):
        return
    exp._render_webpdf_with_nbconvert = _render_webpdf_subprocess
    exp._swf8_webpdf_subprocess = True


def _apply() -> None:
    _patch_webpdf_exporter()
    _patch_marimo_renderer()


_apply()
