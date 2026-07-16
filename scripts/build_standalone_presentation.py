#!/usr/bin/env python3
"""Embed local presentation images so the HTML can be shared as one file."""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
from pathlib import Path

IMAGE_SOURCE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")')


def embed_images(source: Path, output: Path) -> None:
    html = source.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        reference = match.group(2)
        if reference.startswith("data:"):
            return match.group(0)
        asset = (source.parent / reference).resolve()
        if not asset.is_relative_to(source.parent.resolve()):
            raise ValueError(f"Image is outside the presentation directory: {reference}")
        if not asset.is_file():
            raise FileNotFoundError(asset)
        mime_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(asset.read_bytes()).decode("ascii")
        return f"{match.group(1)}data:{mime_type};base64,{encoded}{match.group(3)}"

    standalone = IMAGE_SOURCE.sub(replace, html)
    marker = "<!-- Self-contained build: all presentation images are embedded below. -->\n"
    standalone = standalone.replace("<!doctype html>\n", f"<!doctype html>\n{marker}", 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(standalone, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="docs/presentation_en_10min.html",
        type=Path,
    )
    parser.add_argument(
        "--output",
        default="docs/presentation_en_10min_standalone.html",
        type=Path,
    )
    args = parser.parse_args()
    embed_images(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
