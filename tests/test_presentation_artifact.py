import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "presentation_en_10min.html"
STANDALONE = ROOT / "docs" / "presentation_en_10min_standalone.html"


def test_presentation_is_complete_and_shareable() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    image_sources = re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', source)
    assert source.count('<section class="slide') == 11
    assert source.count('<aside class="speaker-notes') == 11
    assert len(image_sources) == 6
    assert all((SOURCE.parent / reference).is_file() for reference in image_sources)

    standalone = STANDALONE.read_text(encoding="utf-8")
    assert standalone.count("data:image/png;base64,") == 6
    assert 'src="results/figures/' not in standalone
    assert "https://" not in standalone
    assert "http://" not in standalone
