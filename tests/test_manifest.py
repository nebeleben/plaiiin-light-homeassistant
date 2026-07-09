"""Sanity checks for integration metadata."""
import json
from pathlib import Path

from custom_components.plaiiinlight.const import DOMAIN

MANIFEST = (
    Path(__file__).parent.parent / "custom_components" / "plaiiinlight" / "manifest.json"
)


def test_manifest_matches_const():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["zeroconf"] == ["_plaiiinlight._tcp.local."]
    assert manifest["requirements"] == []
    assert manifest["iot_class"] == "local_polling"
