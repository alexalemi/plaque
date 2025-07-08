"""The main python file parser"""

import re
from enum import Enum
from typing import TextIO, Generator
from .cell import Cell, CellType


def parse_cell_boundary(line: str) -> tuple[str, CellType, dict[str, str]]:
    """Read the tags from a cell boundary line.

    Format follows jupytext:
        # %% Optional title [markdown] key1="val1" key2=val2
    """
    # Remove the prefix and work with the remainder
    content = line.strip()
    if not content.startswith("# %%"):
        raise ValueError(f"Invalid cell boundary line: {line}")

    content = content[4:].strip()  # Remove "# %%" and whitespace

    # Look for [cell_type] marker
    cell_type = CellType.CODE
    cell_type_match = re.search(r"\[([^\]]*)\]", content)
    if cell_type_match:
        cell_type_str = cell_type_match.group(1)
        if cell_type_str.lower() in ("markdown", "md"):
            cell_type = CellType.MARKDOWN
        # Remove the [cell_type] part from content
        content = (
            content[: cell_type_match.start()].strip()
            + " "
            + content[cell_type_match.end() :].strip()
        )
        content = content.strip()

    # Now split title from metadata
    title = ""
    metadata_str = ""

    # Look for key=value patterns - check if the content starts with metadata
    if re.match(r'^\w+=["\']?[^"\']*', content):
        # Content starts with metadata, no title
        title = ""
        metadata_str = content
    else:
        # Look for metadata after whitespace
        metadata_match = re.search(r'\s+(\w+=["\']?[^"\']*)', content)
        if metadata_match:
            title = content[: metadata_match.start()].strip()
            metadata_str = content[metadata_match.start() :].strip()
        else:
            title = content.strip()
            metadata_str = ""

    # Parse metadata
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
                        cell.content = cell.content.strip()
                        yield cell

                    if line.startswith("# %%"):
                        # we just hit a cell boundary
                        (title, celltype, metadata) = parse_cell_boundary(line)
                        if title:
                            metadata = {"title": title} | metadata
                        state = (
                            State.MARKDOWN
                            if celltype == CellType.MARKDOWN
                            else State.CODE
                        )
                        cell = Cell(celltype, "", i + 1, metadata=metadata)

                    elif line.startswith("'''"):
                        cell = Cell(CellType.MARKDOWN, "", i + 1)
                        stripped_line = line.strip()
                        if len(stripped_line) > 6 and stripped_line.endswith("'''"):
                            # it's already closed, its a one liner
                            cell.content = (
                                line.removeprefix("'''")
                                .rstrip()
                                .removesuffix("'''")
                                .strip()
                            )
                            yield cell
                            cell = Cell(CellType.CODE, "", i + 2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_SINGLE_QUOTE
                    elif line.startswith('"""'):
                        cell = Cell(CellType.MARKDOWN, "", i + 1)
                        stripped_line = line.strip()
                        if len(stripped_line) > 6 and stripped_line.endswith('"""'):
                            # it's already closed, its a one liner
                            cell.content = (
                                line.removeprefix('"""')
                                .rstrip()
                                .removesuffix('"""')
                                .strip()
                            )
                            yield cell
                            cell = Cell(CellType.CODE, "", i + 2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_DOUBLE_QUOTE

                else:
                    cell.content += line

            case State.MARKDOWN:
                if cell_boundary(line):
                    if cell.content:
                        cell.content = cell.content.strip()
                        yield cell

                    if line.startswith("# %%"):
                        # we just hit a cell boundary
                        (title, celltype, metadata) = parse_cell_boundary(line)
                        metadata = {"title": title} | metadata
                        state = (
                            State.MARKDOWN
                            if celltype == CellType.MARKDOWN
                            else State.CODE
                        )
                        cell = Cell(celltype, "", i + 1, metadata=metadata)

                    elif line.startswith("'''"):
                        cell = Cell(CellType.MARKDOWN, "", i + 1)
                        stripped_line = line.strip()
                        if len(stripped_line) > 6 and stripped_line.endswith("'''"):
                            # it's already closed, its a one liner
                            cell.content = (
                                line.removeprefix("'''")
                                .rstrip()
                                .removesuffix("'''")
                                .strip()
                            )
                            yield cell
                            cell = Cell(CellType.CODE, "", i + 2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_SINGLE_QUOTE
                    elif line.startswith('"""'):
                        cell = Cell(CellType.MARKDOWN, "", i + 1)
                        stripped_line = line.strip()
                        if len(stripped_line) > 6 and stripped_line.endswith('"""'):
                            # it's already closed, its a one liner
                            cell.content = (
                                line.removeprefix('"""')
                                .rstrip()
                                .removesuffix('"""')
                                .strip()
                            )
                            yield cell
                            cell = Cell(CellType.CODE, "", i + 2)
                            state = State.CODE
                        else:
                            state = State.TRIPLE_DOUBLE_QUOTE

                elif not line.startswith("#"):
                    # we aren't in the markdown cell anymore.
                    cell.content = cell.content.strip()
                    yield cell
                    state = State.CODE
                    cell = Cell(CellType.CODE, "", i + 1)

                else:
                    cell.content += line.removeprefix("#").removeprefix(" ")

            case State.TRIPLE_SINGLE_QUOTE:
                # we are inside the triple quote case.
                if line.rstrip().endswith("'''"):
                    # it's already closed, its a one liner
                    cell.content += line.rstrip().removesuffix("'''")
                    cell.content = cell.content.strip()
                    yield cell
                    cell = Cell(CellType.CODE, "", i + 2)
                    state = State.CODE
                else:
                    cell.content += line

            case State.TRIPLE_DOUBLE_QUOTE:
                # we are inside the triple quote case.
                if line.rstrip().endswith('"""'):
                    # it's already closed, its a one liner
                    cell.content += line.rstrip().removesuffix('"""')
                    cell.content = cell.content.strip()
                    yield cell
                    cell = Cell(CellType.CODE, "", i + 2)
                    state = State.CODE
                else:
                    cell.content += line

    if cell.content.strip():
        cell.content = cell.content.strip()
        yield cell


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, "r") as f:
            for cell in parse(f):
                print(
                    f"Type: {cell.type.name}, Line: {cell.lineno}, Metadata: {cell.metadata}"
                )
                print(f"Content:\n{cell.content}")
                print("-" * 40)
    else:
        print("Usage: python parser.py <filename>")
