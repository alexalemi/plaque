"""The HTML Renderer."""

import html
import re
from typing import Any
from .cell import Cell, CellType
from collections.abc import Iterable


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text)


def format_code(content: str) -> str:
    """Format code content with syntax highlighting."""
    # Basic syntax highlighting - could be enhanced with pygments later
    escaped = escape_html(content)
    
    # Simple Python syntax highlighting patterns
    patterns = [
        (r'\b(def|class|import|from|if|else|elif|for|while|try|except|finally|with|as|return|yield|break|continue|pass|lambda|and|or|not|in|is|None|True|False)\b', r'<span class="keyword">\1</span>'),
        (r'#.*$', r'<span class="comment">\g<0></span>'),
        (r'(["\'])(?:(?=(\\?))\2.)*?\1', r'<span class="string">\g<0></span>'),
        (r'\b\d+\.?\d*\b', r'<span class="number">\g<0></span>'),
    ]
    
    for pattern, replacement in patterns:
        escaped = re.sub(pattern, replacement, escaped, flags=re.MULTILINE)
    
    return escaped


def format_markdown(content: str) -> str:
    """Basic markdown formatting."""
    # Convert markdown to HTML (basic implementation)
    text = escape_html(content)
    
    # Headers
    text = re.sub(r'^### (.*$)', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*$)', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*$)', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Bold and italic
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # Code blocks
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # LaTeX equations (basic support)
    text = re.sub(r'\$\$(.*?)\$\$', r'<div class="math-block">\\[\1\\]</div>', text, flags=re.DOTALL)
    text = re.sub(r'\$([^$]+)\$', r'<span class="math-inline">\\(\1\\)</span>', text)
    
    # Convert line breaks to paragraphs
    paragraphs = text.split('\n\n')
    formatted_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            p = f'<p>{p.replace(chr(10), "<br>")}</p>'
        formatted_paragraphs.append(p)
    
    return '\n'.join(formatted_paragraphs)


def format_result(result: Any) -> str:
    """Format cell execution result."""
    if result is None:
        return ""
    
    # Import display manager
    from .display import RichDisplayManager
    display_manager = RichDisplayManager()
    
    # Use rich display manager for formatting
    return display_manager.display(result)


def render_cell(cell: Cell) -> str:
    """Render a single cell to HTML."""
    cell_id = f"cell-{cell.lineno}"
    
    if cell.type == CellType.CODE:
        html_parts = [f'<div class="cell code-cell" id="{cell_id}">']
        
        # Add title if present
        if "title" in cell.metadata:
            html_parts.append(f'<div class="cell-title">{escape_html(cell.metadata["title"])}</div>')
        
        # Add code input
        html_parts.append('<div class="cell-input">')
        html_parts.append('<div class="input-label">In:</div>')
        html_parts.append(f'<pre class="code-content">{format_code(cell.content)}</pre>')
        html_parts.append('</div>')
        
        # Add error output if present
        if cell.error:
            html_parts.append('<div class="cell-error">')
            html_parts.append('<div class="error-label">Error:</div>')
            html_parts.append(f'<pre class="error-content">{escape_html(cell.error)}</pre>')
            html_parts.append('</div>')
        
        # Add result output if present
        if cell.result is not None:
            html_parts.append('<div class="cell-output">')
            html_parts.append('<div class="output-label">Out:</div>')
            html_parts.append(f'<div class="output-content">{format_result(cell.result)}</div>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    elif cell.type == CellType.MARKDOWN:
        html_parts = [f'<div class="cell markdown-cell" id="{cell_id}">']
        
        # Add title if present
        if "title" in cell.metadata:
            html_parts.append(f'<div class="cell-title">{escape_html(cell.metadata["title"])}</div>')
        
        # Add markdown content
        html_parts.append(f'<div class="markdown-content">{format_markdown(cell.content)}</div>')
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    return ""


def get_html_template() -> str:
    """Get the HTML template with CSS styling."""
    import os
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'notebook.html')
    with open(template_path, 'r') as f:
        return f.read()


def format(cells: Iterable[Cell]) -> str:
    """Format cells into a complete HTML document."""
    cell_html = '\n'.join(render_cell(cell) for cell in cells)
    template = get_html_template()
    return template.replace('{content}', cell_html)
