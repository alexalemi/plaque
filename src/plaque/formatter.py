"""The HTML Renderer."""

from .cell import Cell, CellType
from collections.abc import Iterable


def repr(cell: Cell) -> str:
    match cell.type:
        case CellType.CODE:
            out = f"<div class='cell'><div class='code'>{cell.content}</div>"
            if cell.error is not None:
                out += f"<div class='error'>{cell.error}</div>"
            if cell.result is not None:
                out += f"<div class='result'>{cell.result}</div>"
            out += "</div>"
            return out
        case CellType.MARKDOWN:
            return f"<div class='cell'><div class='markdown'>{cell.content}</div></div>"



def format(cells: Iterable[Cell]) -> str:
    return "<html>" + "\n".join(repr(cell) for cell in cells) + "</html>"
