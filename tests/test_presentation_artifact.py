import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "pre.html"
STANDALONE = ROOT / "docs" / "presentation_standalone.html"


def test_presentation_is_complete_and_shareable() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    image_sources = re.findall(r'\ssrc="([^"]+)"', source)
    factor_sources = re.findall(r'\sdata-src="([^"]+)"', source)
    factor_buttons = re.findall(
        r'<button class="factor-button[^"]*"[^>]*data-factor="([^"]+)"', source
    )
    factor_assets = re.findall(r'<img data-factor="([^"]+)" data-kind="([^"]+)" data-src=', source)
    assert source.count('<section class="slide') == 11
    assert "speaker-notes" not in source
    assert len(image_sources) == 5
    assert len(factor_buttons) == 8
    assert len(set(factor_buttons)) == 8
    assert len(factor_sources) == 16
    assert set(factor_assets) == {
        (factor, kind) for factor in factor_buttons for kind in ("ic", "quantiles")
    }
    assert all(
        (SOURCE.parent / reference).is_file() for reference in image_sources + factor_sources
    )

    standalone = STANDALONE.read_text(encoding="utf-8")
    assert "speaker-notes" not in standalone
    assert standalone.count("data:image/png;base64,") == 21
    assert 'src="results/figures/' not in standalone
    assert 'data-src="results/figures/' not in standalone
    assert "https://" not in standalone
    assert "http://" not in standalone


def test_presentation_exports_do_not_include_powerpoint() -> None:
    assert not any(
        path.suffix.lower() in {".ppt", ".pptx"} for path in (ROOT / "docs").rglob("*")
    )


def test_standalone_build_uses_neutral_default_filename(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "pre.html").write_text("<!doctype html>\n<p>Local presentation</p>\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_standalone_presentation.py")],
        cwd=tmp_path,
        check=True,
    )
    assert (docs / "presentation_standalone.html").is_file()
    assert sorted(path.name for path in docs.iterdir()) == [
        "pre.html",
        "presentation_standalone.html",
    ]
