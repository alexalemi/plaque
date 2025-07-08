"""The main Cell class."""

from typing import Any
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

    @property
    def is_code(self) -> bool:
        return self.type == CellType.CODE

    @property
    def is_markdown(self) -> bool:
        return self.type == CellType.MARKDOWN
