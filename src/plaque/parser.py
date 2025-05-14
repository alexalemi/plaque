"""The main python file parser"""

from enum import Enum
from typing import TextIO, Generator
import dataclasses

class CellType(Enum):
    Code = 1
    Markdown = 2

@dataclasses.dataclass
class Cell:
    type: CellType
    content: str
    lineno: int

def parse(input: TextIO) -> Generator[Cell, None, None]:
    lineno = 0
    line = ""
    celltype = CellType.Code
    content = ""

    for i, line in enumerate(input):
        # first see if it starts with our cell markers.

        if line.startswith("# %%"):
            # We've started a new cell, emit the current one.
            if content:
                yield Cell(celltype, content, lineno)

            content = ""
            lineno = i

        elif line.startswith('"""') or line.startswith("'''"):
            if content:
                yield Cell("todo", content, lineno)

            content = line[3:]
            lineno = i

        else:
            content += line

    yield Cell("todo", content, lineno)

        
            

