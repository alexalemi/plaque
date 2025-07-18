"""The HTML Renderer."""

import base64
import html
import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional

from .cell import Cell, CellType
from .display import to_renderable
from .renderables import HTML, JPEG, JSON, Latex, Markdown, PNG, SVG, Text


def _get_cell_image_name(cell_counter: int, extension: str) -> str:
    """Generate a deterministic image filename based on cell execution counter."""
    return f"cell_{cell_counter}_img.{extension}"


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text)


def format_code(content: str) -> str:
    """Format code content with syntax highlighting using Pygments."""
    try:
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatters import HtmlFormatter

        lexer = PythonLexer()
        formatter = HtmlFormatter(
            style="monokai",
            noclasses=True,
            cssclass="highlight",
            nowrap=True,  # Don't wrap in <pre><code>, we'll handle that ourselves
        )
        highlighted = highlight(content, lexer, formatter)
        return f"<pre><code>{highlighted}</code></pre>"
    except ImportError:
        # Fallback to escaped HTML if pygments not available
        return f"<pre><code>{escape_html(content)}</code></pre>"


def format_markdown(content: str) -> str:
    """Convert markdown to HTML using the markdown library."""
    try:
        import markdown
        from markdown.extensions import codehilite, fenced_code, tables, toc  # noqa: F401

        # Configure markdown with useful extensions
        md = markdown.Markdown(
            extensions=[
                "codehilite",
                "fenced_code",
                "tables",
                "toc",
                "nl2br",  # Convert newlines to <br>
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "use_pygments": True,
                }
            },
        )

        html = md.convert(content)

        return html

    except ImportError:
        # Fallback to basic HTML conversion
        text = escape_html(content)

        # Headers
        text = re.sub(r"^### (.*$)", r"<h3>\1</h3>", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.*$)", r"<h2>\1</h2>", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.*$)", r"<h1>\1</h1>", text, flags=re.MULTILINE)

        # Bold and italic
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)

        # Code blocks
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        # Convert line breaks to paragraphs
        paragraphs = text.split("\n\n")
        formatted_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith("<"):
                p = f"<p>{p.replace(chr(10), '<br>')}</p>"
            formatted_paragraphs.append(p)

        return "\n".join(formatted_paragraphs)


def format_result(
    result: Any, image_dir: Optional[Path] = None, cell_counter: Optional[int] = None
) -> str:
    """Format cell execution result by converting it to a renderable and then to HTML."""
    if result is None:
        return ""

    renderable = to_renderable(result)

    match renderable:
        case HTML(content):
            return content
        case Markdown(content):
            return format_markdown(content)
        case Text(content):
            return f'<pre class="result-output">{escape_html(content)}</pre>'
        case PNG(content):
            if image_dir is not None and cell_counter is not None:
                # Save to file and return file reference
                filename = _get_cell_image_name(cell_counter, "png")
                filepath = image_dir / filename
                with open(filepath, "wb") as f:
                    f.write(content)
                return f'<div class="png-output"><img src="/images/{filename}" style="max-width: 100%; height: auto;"></div>'
            else:
                # Use base64 data URI (default behavior)
                png_b64 = base64.standard_b64encode(content).decode()
                return f'<div class="png-output"><img src="data:image/png;base64,{png_b64}" style="max-width: 100%; height: auto;"></div>'
        case JPEG(content):
            if image_dir is not None and cell_counter is not None:
                # Save to file and return file reference
                filename = _get_cell_image_name(cell_counter, "jpg")
                filepath = image_dir / filename
                with open(filepath, "wb") as f:
                    f.write(content)
                return f'<div class="jpeg-output"><img src="/images/{filename}" style="max-width: 100%; height: auto;"></div>'
            else:
                # Use base64 data URI (default behavior)
                jpeg_b64 = base64.standard_b64encode(content).decode()
                return f'<div class="jpeg-output"><img src="data:image/jpeg;base64,{jpeg_b64}" style="max-width: 100%; height: auto;"></div>'
        case SVG(content):
            return f'<div class="svg-output">{content}</div>'
        case Latex(content):
            return f'<div class="math-block">\\[{content}\\]</div>'
        case JSON(content):
            json_str = json.dumps(content, indent=2)
            return f'<pre class="json-output">{escape_html(json_str)}</pre>'
        case _:
            return f'<pre class="result-output">{escape_html(str(renderable))}</pre>'


def render_cell(cell: Cell, image_dir: Optional[Path] = None) -> str:
    """Render a single cell to HTML."""
    cell_id = f"cell-{cell.lineno}"

    if cell.type == CellType.CODE:
        html_parts = [f'<div class="cell code-cell" id="{cell_id}">']

        # Add code counter
        html_parts.append(f'<div class="cell-counter">{cell.counter}</div>')

        # Add title if present
        if "title" in cell.metadata:
            html_parts.append(
                f'<div class="cell-title">{escape_html(cell.metadata["title"])}</div>'
            )

        # Add code input
        html_parts.append('<div class="cell-input">')
        html_parts.append(
            f'<div class="code-content">{format_code(cell.content)}</div>'
        )
        html_parts.append("</div>")

        # Add stdout output if present
        if cell.stdout:
            html_parts.append('<div class="cell-stdout">')
            html_parts.append(
                f'<pre class="stdout-content">{escape_html(cell.stdout)}</pre>'
            )
            html_parts.append("</div>")

        # Add stderr output if present
        if cell.stderr:
            html_parts.append('<div class="cell-stderr">')
            html_parts.append(
                f'<pre class="stderr-content">{escape_html(cell.stderr)}</pre>'
            )
            html_parts.append("</div>")

        # Add error output if present
        if cell.error:
            html_parts.append('<div class="cell-error">')
            html_parts.append('<div class="error-label">Error:</div>')
            html_parts.append(
                f'<pre class="error-content">{escape_html(cell.error)}</pre>'
            )
            html_parts.append("</div>")

        # Add result output if present
        if cell.result is not None:
            html_parts.append('<div class="cell-output">')
            html_parts.append(
                f'<div class="output-content">{format_result(cell.result, image_dir, cell.counter)}</div>'
            )
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    elif cell.type == CellType.MARKDOWN:
        # Render markdown without cell wrapper for natural document flow
        html_parts = []

        # Add title if present (as a standalone heading)
        if "title" in cell.metadata:
            html_parts.append(
                f'<h3 class="markdown-title">{escape_html(cell.metadata["title"])}</h3>'
            )

        # Check if this is an f-string markdown cell
        if cell.metadata.get("string_prefix", "").startswith("f"):
            # Handle f-string markdown cells
            if cell.error:
                # Show error for f-strings that failed to execute
                html_parts.append(f'<div class="cell code-cell" id="{cell_id}">')
                html_parts.append(f'<div class="cell-counter">{cell.counter}</div>')
                html_parts.append('<div class="cell-error">')
                html_parts.append('<div class="error-label">ERROR</div>')
                html_parts.append(
                    f'<pre class="error-content">{escape_html(cell.error)}</pre>'
                )
                html_parts.append("</div>")
                html_parts.append("</div>")
            elif cell.result is not None:
                # Use the evaluated result as the markdown content
                content = str(cell.result)
                # Add execution counter for f-strings
                html_parts.append(
                    f'<div class="cell-counter" style="float: right; color: #888; font-family: monospace; font-size: 12px; padding: 0.5em;">{cell.counter}</div>'
                )
                html_parts.append(
                    f'<div class="markdown-content" id="{cell_id}">{format_markdown(content)}</div>'
                )
            else:
                # Fallback: show the original content
                html_parts.append(
                    f'<div class="markdown-content" id="{cell_id}">{format_markdown(cell.content)}</div>'
                )
        else:
            # Regular markdown cell
            html_parts.append(
                f'<div class="markdown-content" id="{cell_id}">{format_markdown(cell.content)}</div>'
            )

        return "\n".join(html_parts)

    return ""


def get_html_template() -> str:
    """Get the HTML template with CSS styling."""

    template_path = os.path.join(
        os.path.dirname(__file__), "templates", "notebook.html"
    )
    with open(template_path, "r") as f:
        return f.read()


def format(cells: Iterable[Cell], image_dir: Optional[Path] = None) -> str:
    """Format cells into a complete HTML document."""
    cell_html = "\n".join(render_cell(cell, image_dir) for cell in cells)
    template = get_html_template()
    return template.replace("{content}", cell_html)
