"""Craft Web Server: host and update Craft apps' web builds on a local network."""
from pathlib import Path

try:
    __version__ = (Path(__file__).resolve().parents[1] / "VERSION").read_text(
        encoding="utf-8").strip() or "0.0.0"
except OSError:
    __version__ = "0.0.0"
