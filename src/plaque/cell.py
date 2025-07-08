"""The main Cell class."""

from typing import Any, Self
from enum import Enum
import dataclasses


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


empty_code_cell = Cell(CellType.CODE, "", -1)
