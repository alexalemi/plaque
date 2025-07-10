"""The main Cell class."""

from typing import Any, Self
from enum import Enum
import dataclasses
import hashlib


class CellType(Enum):
    CODE = 1
    MARKDOWN = 2


@dataclasses.dataclass
class Cell:
    type: CellType
    content: str
    lineno: int
    metadata: dict[str, str] = dataclasses.field(default_factory=dict)
    error: None | str = None
    result: Any | None = None
    counter: int = 0
    stdout: str = ""
    stderr: str = ""
    # Dependency tracking fields
    provides: set[str] = dataclasses.field(default_factory=set)
    requires: set[str] = dataclasses.field(default_factory=set)
    depends_on: set[int] = dataclasses.field(default_factory=set)
    content_hash: str = ""

    @property
    def is_code(self) -> bool:
        return self.type == CellType.CODE

    @property
    def is_markdown(self) -> bool:
        return self.type == CellType.MARKDOWN

    def copy_execution(self, other: Self):
        self.error = other.error
        self.counter = other.counter
        self.result = other.result
        self.stdout = other.stdout
        self.stderr = other.stderr

    def compute_content_hash(self) -> str:
        """Compute a hash of the cell content for change detection."""
        content = self.content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()[:16]  # First 16 chars for brevity

    def update_content_hash(self):
        """Update the content hash based on current content."""
        self.content_hash = self.compute_content_hash()

    def has_content_changed(self) -> bool:
        """Check if the content has changed since last hash update."""
        return self.content_hash != self.compute_content_hash()


empty_code_cell = Cell(CellType.CODE, "", -1)
