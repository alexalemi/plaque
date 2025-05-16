"""The HTML Renderer."""

from .cell import Cell, CellType
from collections.abc import Iterable


def repr(cell: Cell) -> str:
    match cell.type:
        case CellType.CODE:
            out = f"<cell><code>{cell.content}</code>"
            if cell.error is not None:
                out += f"<error>{cell.error}</error>"
            if cell.result is not None:
                out += f"<result>{cell.result}</result>"
            out += "</cell>"
            return out
        case CellType.MARKDOWN:
            return f"<cell><markdown>{cell.content}</markdown></cell>"



def format(cells: Iterable[Cell]) -> str:
    return "<html>" + "\n".join(repr(cell) for cell in cells) + "</html>"
