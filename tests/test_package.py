import json
from pathlib import Path


ROOT = Path(__file__).parents[1] / "custom_components" / "weatheri_forecast"


def test_manifest_is_repository_ready():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "weatheri_forecast"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "cloud_polling"
    assert manifest["version"] == "0.2.3"
    assert any(item.startswith("beautifulsoup4") for item in manifest["requirements"])


def test_translations_match_strings():
    strings = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))
    for language in ("en", "ko"):
        translated = json.loads(
            (ROOT / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )
        assert translated["config"]["error"].keys() == strings["config"]["error"].keys()
        assert translated["entity"]["sensor"].keys() == strings["entity"]["sensor"].keys()
        assert translated["entity"]["binary_sensor"].keys() == strings["entity"]["binary_sensor"].keys()


def test_repository_metadata_and_documentation():
    repository = ROOT.parents[1]
    hacs = json.loads((repository / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["country"] == "KR"
    assert hacs["homeassistant"] == "2026.3.0"
    readme = (repository / "README.md").read_text(encoding="utf-8")
    for heading in ("## 한국어", "## English", "### 설치", "### Installation", "### 제거", "### Removal"):
        assert heading in readme
    assert (repository / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_brand_assets_have_required_dimensions_and_alpha():
    from PIL import Image

    expected = {
        "icon.png": (256, 256), "icon@2x.png": (512, 512),
        "dark_icon.png": (256, 256), "dark_icon@2x.png": (512, 512),
        "logo.png": (896, 256), "logo@2x.png": (1792, 512),
        "dark_logo.png": (896, 256), "dark_logo@2x.png": (1792, 512),
    }
    for name, size in expected.items():
        image = Image.open(ROOT / "brand" / name)
        assert image.size == size
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0
