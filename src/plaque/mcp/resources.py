"""Resource provider for MCP server - read-only notebook inspection."""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs
import time

from ..processor import Processor
from ..api_formatter import cell_to_json, notebook_state_to_json, format_result


class ResourceProvider:
    """Provides read-only resources for notebook inspection."""

    def __init__(self, processor: Processor):
        self.processor = processor

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources."""
        resources = [
            {
                "uri": "notebook://cells",
                "name": "All Cells",
                "description": "Complete listing of all notebook cells with metadata",
                "mimeType": "application/json",
            },
            {
                "uri": "notebook://state",
                "name": "Notebook State",
                "description": "Overall notebook status and execution statistics",
                "mimeType": "application/json",
            },
            {
                "uri": "notebook://errors",
                "name": "Error Summary",
                "description": "All cells with errors and error details",
                "mimeType": "application/json",
            },
            {
                "uri": "notebook://dependencies",
                "name": "Dependency Graph",
                "description": "Variable dependencies between cells",
                "mimeType": "application/json",
            },
            {
                "uri": "notebook://outputs",
                "name": "All Outputs",
                "description": "All cell outputs (text, images, dataframes)",
                "mimeType": "application/json",
            },
            {
                "uri": "notebook://variables",
                "name": "Variable State",
                "description": "Current state of all variables in the notebook environment",
                "mimeType": "application/json",
            },
        ]

        # Add individual cell resources
        for i, cell in enumerate(self.processor.cells):
            resources.extend(
                [
                    {
                        "uri": f"notebook://cell/{i}",
                        "name": f"Cell {i}",
                        "description": f"Complete details for cell {i} at line {cell.lineno}",
                        "mimeType": "application/json",
                    },
                    {
                        "uri": f"notebook://cell/{i}/input",
                        "name": f"Cell {i} Input",
                        "description": f"Source code for cell {i}",
                        "mimeType": "text/plain",
                    },
                    {
                        "uri": f"notebook://cell/{i}/output",
                        "name": f"Cell {i} Output",
                        "description": f"Execution results for cell {i}",
                        "mimeType": "application/json",
                    },
                ]
            )

        return resources

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        """Read a specific resource by URI."""
        parsed_uri = urlparse(uri)
        if parsed_uri.scheme != "notebook":
            raise ValueError(f"Unsupported URI scheme: {parsed_uri.scheme}")

        path = parsed_uri.path.lstrip("/")

        if path == "cells":
            return await self._get_all_cells()
        elif path == "state":
            return await self._get_notebook_state()
        elif path == "errors":
            return await self._get_error_summary()
        elif path == "dependencies":
            return await self._get_dependency_graph()
        elif path == "outputs":
            return await self._get_all_outputs()
        elif path == "variables":
            return await self._get_variable_state()
        elif path.startswith("cell/"):
            return await self._get_cell_resource(path)
        else:
            raise ValueError(f"Unknown resource path: {path}")

    async def _get_all_cells(self) -> List[Dict[str, Any]]:
        """Get all cells with complete metadata."""
        cells_data = []
        for i, cell in enumerate(self.processor.cells):
            cell_data = cell_to_json(cell, i)
            cells_data.append(cell_data)

        return [
            {
                "uri": "notebook://cells",
                "mimeType": "application/json",
                "text": json.dumps(
                    {
                        "cells": cells_data,
                        "total": len(cells_data),
                        "timestamp": time.time(),
                    },
                    indent=2,
                ),
            }
        ]

    async def _get_notebook_state(self) -> List[Dict[str, Any]]:
        """Get overall notebook state."""
        state = notebook_state_to_json(self.processor.cells, time.time())

        # Add more detailed statistics
        state["execution_summary"] = {
            "total_executions": sum(
                1 for cell in self.processor.cells if cell.counter > 0
            ),
            "successful_executions": sum(
                1
                for cell in self.processor.cells
                if cell.counter > 0 and not cell.error
            ),
            "failed_executions": sum(1 for cell in self.processor.cells if cell.error),
            "pending_executions": sum(
                1 for cell in self.processor.cells if cell.is_code and cell.counter == 0
            ),
        }

        return [
            {
                "uri": "notebook://state",
                "mimeType": "application/json",
                "text": json.dumps(state, indent=2),
            }
        ]

    async def _get_error_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all errors."""
        errors = []
        for i, cell in enumerate(self.processor.cells):
            if cell.error:
                errors.append(
                    {
                        "cell_index": i,
                        "line_number": cell.lineno,
                        "cell_type": "code" if cell.is_code else "markdown",
                        "error": cell.error,
                        "content": cell.content,
                        "execution_count": cell.counter,
                        "stderr": cell.stderr,
                    }
                )

        return [
            {
                "uri": "notebook://errors",
                "mimeType": "application/json",
                "text": json.dumps(
                    {
                        "errors": errors,
                        "total_errors": len(errors),
                        "timestamp": time.time(),
                    },
                    indent=2,
                ),
            }
        ]

    async def _get_dependency_graph(self) -> List[Dict[str, Any]]:
        """Get variable dependency graph."""
        dependencies = []
        variables = {}

        for i, cell in enumerate(self.processor.cells):
            if cell.is_code:
                cell_info = {
                    "cell_index": i,
                    "line_number": cell.lineno,
                    "provides": list(cell.provides),
                    "requires": list(cell.requires),
                    "depends_on": list(cell.depends_on),
                }
                dependencies.append(cell_info)

                # Track variable definitions
                for var in cell.provides:
                    variables[var] = {
                        "defined_in_cell": i,
                        "line_number": cell.lineno,
                        "execution_count": cell.counter,
                    }

        return [
            {
                "uri": "notebook://dependencies",
                "mimeType": "application/json",
                "text": json.dumps(
                    {
                        "cell_dependencies": dependencies,
                        "variables": variables,
                        "timestamp": time.time(),
                    },
                    indent=2,
                ),
            }
        ]

    async def _get_all_outputs(self) -> List[Dict[str, Any]]:
        """Get all cell outputs."""
        outputs = []

        for i, cell in enumerate(self.processor.cells):
            if cell.is_code and (cell.result is not None or cell.stdout or cell.stderr):
                output = {
                    "cell_index": i,
                    "line_number": cell.lineno,
                    "execution_count": cell.counter,
                    "stdout": cell.stdout,
                    "stderr": cell.stderr,
                }

                if cell.result is not None:
                    output["result"] = format_result(cell.result, include_base64=True)

                outputs.append(output)

        return [
            {
                "uri": "notebook://outputs",
                "mimeType": "application/json",
                "text": json.dumps(
                    {
                        "outputs": outputs,
                        "total_outputs": len(outputs),
                        "timestamp": time.time(),
                    },
                    indent=2,
                ),
            }
        ]

    async def _get_variable_state(self) -> List[Dict[str, Any]]:
        """Get current variable state from the processor environment."""
        variables = {}

        # Get variables from the processor's environment
        if hasattr(self.processor, "environment") and hasattr(
            self.processor.environment, "globals"
        ):
            env_vars = self.processor.environment.globals
            for name, value in env_vars.items():
                if not name.startswith("_"):  # Skip private variables
                    try:
                        variables[name] = {
                            "type": type(value).__name__,
                            "value": str(value)[:500],  # Truncate long values
                            "repr": repr(value)[:200]
                            if hasattr(value, "__repr__")
                            else str(value)[:200],
                        }
                    except Exception as e:
                        variables[name] = {
                            "type": type(value).__name__,
                            "value": f"<Error getting value: {e}>",
                            "repr": f"<Error: {e}>",
                        }

        return [
            {
                "uri": "notebook://variables",
                "mimeType": "application/json",
                "text": json.dumps(
                    {
                        "variables": variables,
                        "total_variables": len(variables),
                        "timestamp": time.time(),
                    },
                    indent=2,
                ),
            }
        ]

    async def _get_cell_resource(self, path: str) -> List[Dict[str, Any]]:
        """Get resource for a specific cell."""
        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid cell path: {path}")

        try:
            cell_index = int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid cell index: {parts[1]}")

        if cell_index < 0 or cell_index >= len(self.processor.cells):
            raise ValueError(f"Cell index out of range: {cell_index}")

        cell = self.processor.cells[cell_index]

        # Handle different cell resource types
        if len(parts) == 2:
            # Full cell details
            cell_data = cell_to_json(cell, cell_index)
            return [
                {
                    "uri": f"notebook://cell/{cell_index}",
                    "mimeType": "application/json",
                    "text": json.dumps(cell_data, indent=2),
                }
            ]
        elif len(parts) == 3 and parts[2] == "input":
            # Just the input/source code
            return [
                {
                    "uri": f"notebook://cell/{cell_index}/input",
                    "mimeType": "text/plain",
                    "text": cell.content,
                }
            ]
        elif len(parts) == 3 and parts[2] == "output":
            # Just the output
            output_data = {
                "cell_index": cell_index,
                "execution_count": cell.counter,
                "error": cell.error,
                "stdout": cell.stdout,
                "stderr": cell.stderr,
            }

            if cell.result is not None:
                output_data["result"] = format_result(cell.result, include_base64=True)

            return [
                {
                    "uri": f"notebook://cell/{cell_index}/output",
                    "mimeType": "application/json",
                    "text": json.dumps(output_data, indent=2),
                }
            ]
        else:
            raise ValueError(f"Unknown cell resource type: {path}")
