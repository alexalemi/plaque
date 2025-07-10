"""AST-based parser for plaque notebook files.

This module provides a more robust parser using Python's AST module to properly
handle cell boundaries and extract cell content. It supports both traditional
# %% markers and top-level triple-quoted strings as cell boundaries.
"""

import ast
import re
from typing import TextIO, Generator, List, Tuple, Optional, Dict, Any
from .cell import Cell, CellType


class CellBoundary:
    """Represents a cell boundary in the source code."""

    def __init__(
        self,
        line_no: int,
        boundary_type: str,
        title: str = "",
        cell_type: CellType = CellType.CODE,
        metadata: Dict[str, str] = None,
    ):
        self.line_no = line_no
        self.boundary_type = boundary_type  # 'marker' or 'string'
        self.title = title
        self.cell_type = cell_type
        self.metadata = metadata or {}


class ASTParser:
    """AST-based parser for plaque notebook files."""

    def __init__(self):
        self.source_lines: List[str] = []
        self.cell_boundaries: List[CellBoundary] = []

    def parse_cell_boundary(self, line: str) -> Tuple[str, CellType, Dict[str, str]]:
        """Parse a cell boundary line to extract title, type, and metadata.

        Format follows jupytext:
            # %% Optional title [markdown] key1="val1" key2=val2
        """
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

    def _find_cell_boundaries(self, source: str) -> List[CellBoundary]:
        """Find all cell boundaries in the source code."""
        boundaries = []
        lines = source.split("\n")

        # Find # %% markers
        for i, line in enumerate(lines):
            if line.strip().startswith("# %%"):
                try:
                    title, cell_type, metadata = self.parse_cell_boundary(line)
                    if title:
                        metadata = {"title": title} | metadata
                    boundaries.append(
                        CellBoundary(
                            line_no=i + 1,
                            boundary_type="marker",
                            title=title,
                            cell_type=cell_type,
                            metadata=metadata,
                        )
                    )
                except ValueError:
                    # Skip invalid cell boundaries
                    continue

        # Find top-level triple-quoted strings using AST
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    # Check if it's a string constant at module level
                    if isinstance(node.value.value, str) and hasattr(node, "lineno"):
                        # This is a top-level string - treat as markdown cell
                        boundaries.append(
                            CellBoundary(
                                line_no=node.lineno,
                                boundary_type="string",
                                cell_type=CellType.MARKDOWN,
                            )
                        )
        except SyntaxError:
            # If we can't parse the AST, just use the marker boundaries
            pass

        # Sort boundaries by line number
        boundaries.sort(key=lambda x: x.line_no)
        return boundaries

    def _extract_cell_content(
        self, start_line: int, end_line: int, boundary_type: str, cell_type: CellType
    ) -> str:
        """Extract content for a cell between given line numbers."""
        if boundary_type == "marker":
            # For marker boundaries, skip the boundary line itself
            content_lines = self.source_lines[start_line:end_line]
        elif boundary_type == "string":
            # For string boundaries, we need to extract the string content
            # Find the string literal and extract its content
            content_lines = []
            in_string = False
            string_delimiter = None

            for i in range(start_line - 1, min(end_line, len(self.source_lines))):
                line = self.source_lines[i]

                if not in_string:
                    # Look for start of string
                    if line.strip().startswith('"""'):
                        in_string = True
                        string_delimiter = '"""'
                        # Extract content after opening delimiter
                        content = line.strip()[3:]
                        if content.endswith('"""') and len(content) > 3:
                            # Single line string
                            content_lines.append(content[:-3])
                            break
                        elif content:
                            content_lines.append(content)
                    elif line.strip().startswith("'''"):
                        in_string = True
                        string_delimiter = "'''"
                        # Extract content after opening delimiter
                        content = line.strip()[3:]
                        if content.endswith("'''") and len(content) > 3:
                            # Single line string
                            content_lines.append(content[:-3])
                            break
                        elif content:
                            content_lines.append(content)
                else:
                    # We're inside a string
                    if line.rstrip().endswith(string_delimiter):
                        # End of string
                        content_lines.append(line.rstrip()[:-3])
                        break
                    else:
                        content_lines.append(line)
        else:
            # Regular code content
            content_lines = self.source_lines[start_line:end_line]

        return "\n".join(content_lines).strip()

    def _find_string_end(self, start_line: int) -> int:
        """Find the end line of a string that starts at start_line."""
        line = self.source_lines[start_line - 1]

        # Check if it's a single-line string
        if line.strip().startswith('"""'):
            content = line.strip()[3:]
            if content.endswith('"""') and len(content) > 3:
                return start_line
        elif line.strip().startswith("'''"):
            content = line.strip()[3:]
            if content.endswith("'''") and len(content) > 3:
                return start_line

        # Multi-line string, find the closing delimiter
        delimiter = '"""' if line.strip().startswith('"""') else "'''"

        for i in range(start_line, len(self.source_lines)):
            if self.source_lines[i].rstrip().endswith(delimiter):
                return i + 1

        # If we don't find a closing delimiter, assume it goes to the end
        return len(self.source_lines)

    def parse(self, input: TextIO) -> Generator[Cell, None, None]:
        """Parse the input and yield Cell objects."""
        source = input.read()
        self.source_lines = source.split("\n")

        # Find all cell boundaries
        self.cell_boundaries = self._find_cell_boundaries(source)

        # If no boundaries found, treat the entire file as one code cell
        if not self.cell_boundaries:
            if source.strip():
                yield Cell(CellType.CODE, source.strip(), lineno=1)
            return

        # Process cells between boundaries
        prev_end = 0

        for i, boundary in enumerate(self.cell_boundaries):
            # Check if there's content before this boundary
            if boundary.line_no > prev_end + 1:
                # There's content before this boundary - create a code cell
                content = self._extract_cell_content(
                    prev_end, boundary.line_no - 1, "code", CellType.CODE
                )
                if content.strip():
                    yield Cell(CellType.CODE, content, lineno=prev_end + 1)

            # For string boundaries, we need to find where the string ends
            if boundary.boundary_type == "string":
                # Find the end of the string
                string_end = self._find_string_end(boundary.line_no)
                cell_end = string_end
            else:
                # For marker boundaries, determine the end normally
                if i + 1 < len(self.cell_boundaries):
                    cell_end = self.cell_boundaries[i + 1].line_no - 1
                else:
                    cell_end = len(self.source_lines)

            # Extract content for this cell
            content = self._extract_cell_content(
                boundary.line_no, cell_end, boundary.boundary_type, boundary.cell_type
            )

            if content.strip():
                yield Cell(
                    boundary.cell_type,
                    content,
                    lineno=boundary.line_no,
                    metadata=boundary.metadata,
                )

            prev_end = cell_end

        # Handle any remaining content after the last boundary
        if prev_end < len(self.source_lines):
            content = self._extract_cell_content(
                prev_end, len(self.source_lines), "code", CellType.CODE
            )
            if content.strip():
                yield Cell(CellType.CODE, content, lineno=prev_end + 1)


def parse_ast(input: TextIO) -> Generator[Cell, None, None]:
    """Parse input using AST-based parser."""
    parser = ASTParser()
    yield from parser.parse(input)
