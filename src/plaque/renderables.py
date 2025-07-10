"""Renderable data classes for rich display output."""

from dataclasses import dataclass
from typing import Any


@dataclass
class HTML:
    """Represents an HTML string that should be rendered directly."""

    content: str


@dataclass
class Markdown:
    """Represents a Markdown string to be converted to HTML."""

    content: str


@dataclass
class Text:
    """Represents plain text that should be escaped and wrapped in <pre>."""

    content: str


@dataclass
class PNG:
    """Represents PNG image data."""

    content: bytes


@dataclass
class JPEG:
    """Represents JPEG image data."""

    content: bytes


@dataclass
class SVG:
    """Represents an SVG image string."""

    content: str


@dataclass
class Latex:
    """Represents a LaTeX string to be rendered."""

    content: str


@dataclass
class JSON:
    """Represents a JSON-serializable object."""

    content: Any
