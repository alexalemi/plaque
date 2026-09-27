"""API formatter for converting Cell objects to JSON for agent consumption."""

import base64
from typing import Any, Dict, List, Optional
from pathlib import Path

from .cell import Cell, CellType
from .renderables import PNG, JPEG, SVG, HTML, JSON as JSONRenderable, Text, Markdown


def to_ms(timestamp: Optional[float]) -> Optional[int]:
    """Convert a time.time() timestamp to integer milliseconds for the API.

    All timestamps exposed over HTTP use this unit, so agents can compare
    them directly (e.g. `forked_from_update` against `last_update`).
    """
    if timestamp is None:
        return None
    return int(timestamp * 1000)


def format_result(
    result: Any,
    image_dir: Optional[Path] = None,
    cell_counter: Optional[int] = None,
    include_base64: bool = False,
) -> Dict[str, Any]:
    """Convert a cell result to a JSON-serializable format."""
    if result is None:
        return None

    # Handle image types
    if isinstance(result, PNG):
        if image_dir and cell_counter is not None:
            # Save image and return path reference
            from .formatter import _get_cell_image_name

            filename = _get_cell_image_name(cell_counter, "png")
            filepath = image_dir / filename
            with open(filepath, "wb") as f:
                f.write(result.content)
            response = {
                "type": "image/png",
                "url": f"/images/{filename}",
            }
            if include_base64:
                response["data"] = base64.standard_b64encode(result.content).decode(
                    "utf-8"
                )
            return response
        else:
            return {
                "type": "image/png",
                "data": base64.standard_b64encode(result.content).decode("utf-8"),
            }

    elif isinstance(result, JPEG):
        if image_dir and cell_counter is not None:
            from .formatter import _get_cell_image_name

            filename = _get_cell_image_name(cell_counter, "jpg")
            filepath = image_dir / filename
            with open(filepath, "wb") as f:
                f.write(result.content)
            response = {
                "type": "image/jpeg",
                "url": f"/images/{filename}",
            }
            if include_base64:
                response["data"] = base64.standard_b64encode(result.content).decode(
                    "utf-8"
                )
            return response
        else:
            return {
                "type": "image/jpeg",
                "data": base64.standard_b64encode(result.content).decode("utf-8"),
            }

    elif isinstance(result, SVG):
        return {"type": "image/svg+xml", "data": result.content}

    elif isinstance(result, HTML):
        return {"type": "text/html", "data": result.content}

    elif isinstance(result, JSONRenderable):
        return {"type": "application/json", "data": result.content}

    elif isinstance(result, Markdown):
        return {"type": "text/markdown", "data": result.content}

    elif isinstance(result, Text):
        return {"type": "text/plain", "data": result.content}

    # Handle pandas DataFrame
    elif hasattr(result, "__class__") and result.__class__.__name__ == "DataFrame":
        return {
            "type": "dataframe",
            "shape": list(result.shape),
            "columns": list(result.columns),
            "data": result.to_dict(orient="records"),
        }

    # Handle matplotlib figures
    elif hasattr(result, "__class__") and "Figure" in result.__class__.__name__:
        # Convert matplotlib figure to PNG
        import io

        buf = io.BytesIO()
        result.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        buf.seek(0)
        png_data = buf.read()
        buf.close()

        if image_dir and cell_counter is not None:
            from .formatter import _get_cell_image_name

            filename = _get_cell_image_name(cell_counter, "png")
            filepath = image_dir / filename
            with open(filepath, "wb") as f:
                f.write(png_data)
            response = {
                "type": "image/png",
                "url": f"/images/{filename}",
            }
            if include_base64:
                response["data"] = base64.standard_b64encode(png_data).decode("utf-8")
            return response
        else:
            return {
                "type": "image/png",
                "data": base64.standard_b64encode(png_data).decode("utf-8"),
            }

    # Default: convert to string representation
    else:
        return {"type": "text/plain", "data": str(result)}


def cell_to_json(
    cell: Cell, index: int, image_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Convert a Cell object to a JSON-serializable dictionary."""
    # Determine execution status
    if cell.is_code:
        if cell.error:
            status = "error"
        elif cell.counter > 0:
            status = "success"
        else:
            status = "pending"
    else:
        status = "rendered"

    # Build the response
    response = {
        "index": index,
        "type": "code" if cell.type == CellType.CODE else "markdown",
        "lineno": cell.lineno,
        "is_template": cell.is_template,
        "content": cell.content,
        "metadata": cell.metadata,
    }

    # Add execution info for code cells (including f-string markdown)
    if cell.is_code:
        execution = {
            "counter": cell.counter,
            "status": status,
            "error": cell.error,
            "stdout": cell.stdout,
            "stderr": cell.stderr,
        }

        # Format the result
        if cell.result is not None and cell.is_template:
            # A template's result is the rendered markdown text
            execution["result"] = {"type": "text/markdown", "data": str(cell.result)}
        elif cell.result is not None:
            execution["result"] = format_result(
                cell.result, image_dir, cell.counter, include_base64=False
            )
        else:
            execution["result"] = None

        response["execution"] = execution

    # Add dependency information if available
    if cell.provides or cell.requires or cell.depends_on:
        response["dependencies"] = {
            "provides": list(cell.provides),
            "requires": list(cell.requires),
            "depends_on": list(cell.depends_on),
        }

    return response


def cells_to_json(
    cells: List[Cell], image_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Convert a list of cells to JSON format."""
    return [cell_to_json(cell, i, image_dir) for i, cell in enumerate(cells)]


def notebook_state_to_json(cells: List[Cell], last_update: float) -> Dict[str, Any]:
    """Get the overall notebook state as JSON."""
    code_cells = [c for c in cells if c.type == CellType.CODE]
    runnable_cells = [c for c in cells if c.is_code]
    executed_cells = [c for c in runnable_cells if c.counter > 0]
    error_cells = [c for c in runnable_cells if c.error]

    return {
        "total_cells": len(cells),
        "code_cells": len(code_cells),
        "markdown_cells": len(cells) - len(code_cells),
        "template_cells": sum(c.is_template for c in cells),
        "executed_cells": len(executed_cells),
        "error_cells": len(error_cells),
        "last_update": to_ms(last_update),
        "cells_with_errors": [i for i, c in enumerate(cells) if c.is_code and c.error],
    }
