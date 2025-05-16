"""The main python file parser"""

# %%

import re
from enum import Enum
from typing import TextIO, Generator
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



def parse_cell_boundary(line: str) -> tuple[str, CellType, dict[str, str]]:
    """Read the tags from a cell boundary line.

    Format follows jupytext:
        # %% Optional title [markdown] key1="val1" key2=val2
    """
    # Pattern breakdown:
    # # %%          - literal cell marker
    # \s*           - optional whitespace
    # ([^[]*)       - capture title (everything up to first '[' or end)
    # (?:\[([^\]]*)\])? - optional non-capturing group for [cell_type]
    # \s*           - optional whitespace
    # (.*)          - capture the rest (key-value pairs)

    pattern = r"# %%\s*([^[]*)(?:\[([^\]]*)\])?\s*(.*)"
    match = re.match(pattern, line.strip())

    if not match:
        raise ValueError(f"Invalid cell boundary line: {line}")

    title, cell_type_str, metadata_str = match.groups()
    title = title.strip() if title else ""

    cell_type = CellType.CODE
    if cell_type_str and cell_type_str.lower() in ('markdown', 'md'):
        cell_type = CellType.MARKDOWN

    metadata = {}
    if metadata_str:
        for match in re.finditer(r'(\w+)=["\']?([^"^\']*)', metadata_str):
            key, value = match.groups()
            metadata[key] = value

    return title, cell_type, metadata


def parse(input: TextIO) -> Generator[Cell, None, None]:
    cell = Cell(CellType.CODE, "", lineno=0)

    def cell_boundary(line: str) -> bool:
        return line.startswith(("# %%", '"""', "'''"))

    class State(Enum):
        CODE = 1
        MARKDOWN = 2
        TRIPLE_DOUBLE_QUOTE = 3
        TRIPLE_SINGLE_QUOTE = 4

    state = State.CODE

    for i, line in enumerate(input):

        match state:
            case State.CODE:
                # we are inside the code case.

                if cell_boundary(line):
                    if cell.content.strip():
                        yield cell

                    if line.startswith('# %%'):
                        # we just hit a cell boundary
                        (title, celltype, metadata) = parse_cell_boundary(line)
                        if title:
                            metadata = {'title': title} | metadata
                        state = State.MARKDOWN if celltype == CellType.MARKDOWN else State.CODE
                        cell = Cell(celltype, "", i+1, metadata=metadata)

                    elif line.startswith("'''"):
                        cell = Cell(CellType.MARKDOWN, "", i+1)
                        if line.rstrip().endswith("'''"):
                            # it's already closed, its a one liner
                            cell.content = line.strip("'''").rstrip().rstrip("'''")
                            yield cell
                            cell = Cell(CellType.CODE, "", i+2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_SINGLE_QUOTE
                    elif line.startswith('"""'):
                        cell = Cell(CellType.MARKDOWN, "", i+1)
                        if line.rstrip().endswith('"""'):
                            # it's already closed, its a one liner
                            cell.content = line.strip('"""').rstrip().rstrip('"""')
                            yield cell
                            cell = Cell(CellType.CODE, "", i+2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_DOUBLE_QUOTE

                else:
                    cell.content += line

            case State.MARKDOWN:
                if cell_boundary(line):
                    if cell.content:
                        yield cell

                    if line.startswith('# %%'):
                        # we just hit a cell boundary
                        (title, celltype, metadata) = parse_cell_boundary(line)
                        metadata = {'title': title} | metadata
                        state = State.MARKDOWN if celltype == CellType.MARKDOWN else State.CODE
                        cell = Cell(celltype, "", i+1, metadata=metadata)

                    elif line.startswith("'''"):
                        cell = Cell(CellType.MARKDOWN, "", i+1)
                        if line.rstrip().endswith("'''"):
                            # it's already closed, its a one liner
                            cell.content = line.strip("'''").rstrip().rstrip("'''")
                            yield cell
                            cell = Cell(CellType.CODE, "", i+2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_SINGLE_QUOTE
                    elif line.startswith('"""'):
                        cell = Cell(CellType.MARKDOWN, "", i+1)
                        if line.rstrip().endswith('"""'):
                            # it's already closed, its a one liner
                            cell.content = line.strip('"""').rstrip().rstrip('"""')
                            yield cell
                            cell = Cell(CellType.CODE, "", i+2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_DOUBLE_QUOTE

                elif not line.startswith('#'):
                    # we aren't in the markdown cell anymore.
                    yield cell
                    state = State.CODE
                    cell = Cell(CellType.CODE, "", i+1)

                else:
                    cell.content += line.strip('#')

            case State.TRIPLE_SINGLE_QUOTE:
                # we are inside the triple quote case.
                if line.rstrip().endswith("'''"):
                    # it's already closed, its a one liner
                    cell.content += line.rstrip().rstrip("'''")
                    yield cell
                    cell = Cell(CellType.CODE, "", i+2)
                    state = State.CODE
                else:
                    cell.content += line

            case State.TRIPLE_DOUBLE_QUOTE:
                # we are inside the triple quote case.
                if line.rstrip().endswith('"""'):
                    # it's already closed, its a one liner
                    cell.content += line.rstrip().rstrip('"""')
                    yield cell
                    cell = Cell(CellType.CODE, "", i+2)
                    state = State.CODE
                else:
                    cell.content += line

    if cell.content:
        yield cell


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'r') as f:
            for cell in parse(f):
                print(f"Type: {cell.type.name}, Line: {cell.lineno}, Metadata: {cell.metadata}")
                print(f"Content:\n{cell.content}")
                print("-" * 40)
    else:
        print("Usage: python parser.py <filename>")
