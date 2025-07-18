"""MCP server implementation for Plaque notebooks."""

import json
import sys
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from pathlib import Path
import logging

from ..processor import Processor
from ..cell import Cell
from ..api_formatter import cell_to_json, notebook_state_to_json
from .resources import ResourceProvider
from .prompts import PromptProvider

logger = logging.getLogger(__name__)


class MCPServer:
    """Model Context Protocol server for Plaque notebooks."""

    def __init__(self, notebook_path: Path, processor: Optional[Processor] = None):
        self.notebook_path = notebook_path
        self.processor = processor or Processor()
        self.resource_provider = ResourceProvider(self.processor)
        self.prompt_provider = PromptProvider(self.processor)
        self.client_capabilities = {}
        self.server_capabilities = {
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False},
            "tools": {"listChanged": False},
        }

    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP message."""
        try:
            # Handle requests
            if "id" in message:
                method = message.get("method")
                params = message.get("params", {})

                if method == "initialize":
                    return await self._handle_initialize(message["id"], params)
                elif method == "resources/list":
                    return await self._handle_resources_list(message["id"], params)
                elif method == "resources/read":
                    return await self._handle_resources_read(message["id"], params)
                elif method == "prompts/list":
                    return await self._handle_prompts_list(message["id"], params)
                elif method == "prompts/get":
                    return await self._handle_prompts_get(message["id"], params)
                elif method == "tools/list":
                    return await self._handle_tools_list(message["id"], params)
                elif method == "tools/call":
                    return await self._handle_tools_call(message["id"], params)
                elif method == "ping":
                    return {"jsonrpc": "2.0", "id": message["id"], "result": {}}
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": message["id"],
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                            "data": {"method": method},
                        },
                    }

            # Handle notifications
            elif "method" in message:
                method = message["method"]
                if method == "initialized":
                    await self._handle_initialized(message.get("params", {}))
                elif method == "notifications/cancelled":
                    await self._handle_cancelled(message.get("params", {}))
                # Notifications don't return responses
                return None

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if "id" in message:
                return {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": {"error": str(e)},
                    },
                }

        return None

    async def _handle_initialize(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle initialize request."""
        self.client_capabilities = params.get("capabilities", {})

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "plaque-mcp", "version": "0.3.0"},
                "capabilities": self.server_capabilities,
            },
        }

    async def _handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle initialized notification."""
        logger.info("MCP server initialized")
        # Process the notebook initially
        await self._refresh_notebook()

    async def _handle_cancelled(self, params: Dict[str, Any]) -> None:
        """Handle cancelled notification."""
        request_id = params.get("requestId")
        logger.info(f"Request cancelled: {request_id}")

    async def _handle_resources_list(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = await self.resource_provider.list_resources()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": resources}}

    async def _handle_resources_read(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        if not uri:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": {"missing": "uri"},
                },
            }

        try:
            contents = await self.resource_provider.read_resource(uri)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"contents": contents},
            }
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": {"error": str(e)},
                },
            }

    async def _handle_prompts_list(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle prompts/list request."""
        prompts = await self.prompt_provider.list_prompts()
        return {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": prompts}}

    async def _handle_prompts_get(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle prompts/get request."""
        name = params.get("name")
        if not name:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": {"missing": "name"},
                },
            }

        try:
            prompt = await self.prompt_provider.get_prompt(
                name, params.get("arguments", {})
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": prompt}
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Invalid params",
                    "data": {"error": str(e)},
                },
            }

    async def _handle_tools_list(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = [
            {
                "name": "search",
                "description": "Search notebook cells by content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "explain",
                "description": "Explain code in a specific cell",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cell_index": {
                            "type": "integer",
                            "description": "Cell index to explain",
                        }
                    },
                    "required": ["cell_index"],
                },
            },
        ]

        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

    async def _handle_tools_call(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "search":
            query = arguments.get("query", "")
            results = await self._search_cells(query)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(results)} matching cells:\n"
                            + "\n".join(
                                [f"Cell {r['index']}: {r['preview']}" for r in results]
                            ),
                        }
                    ]
                },
            }

        elif name == "explain":
            cell_index = arguments.get("cell_index")
            if (
                cell_index is None
                or cell_index < 0
                or cell_index >= len(self.processor.cells)
            ):
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid cell index",
                        "data": {"cell_index": cell_index},
                    },
                }

            cell = self.processor.cells[cell_index]
            explanation = await self._explain_cell(cell)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": explanation}]},
            }

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Unknown tool",
                "data": {"tool": name},
            },
        }

    async def _refresh_notebook(self) -> None:
        """Refresh the notebook by re-processing the file."""
        try:
            from ..ast_parser import parse_ast

            with open(self.notebook_path, "r") as f:
                cells = list(parse_ast(f))

            self.processor.process_cells(cells)
            logger.info(f"Refreshed notebook: {len(self.processor.cells)} cells")
        except Exception as e:
            logger.error(f"Error refreshing notebook: {e}")

    async def _search_cells(self, query: str) -> List[Dict[str, Any]]:
        """Search cells by content."""
        query_lower = query.lower()
        results = []

        for i, cell in enumerate(self.processor.cells):
            if query_lower in cell.content.lower():
                results.append(
                    {
                        "index": i,
                        "type": "code" if cell.is_code else "markdown",
                        "preview": cell.content[:100] + "..."
                        if len(cell.content) > 100
                        else cell.content,
                    }
                )

        return results

    async def _explain_cell(self, cell: Cell) -> str:
        """Generate explanation for a cell."""
        explanation = f"Cell at line {cell.lineno}:\n"
        explanation += f"Type: {'Code' if cell.is_code else 'Markdown'}\n"
        explanation += f"Content: {cell.content}\n"

        if cell.is_code:
            explanation += f"Execution count: {cell.counter}\n"
            if cell.error:
                explanation += f"Error: {cell.error}\n"
            elif cell.result is not None:
                explanation += f"Result: {cell.result}\n"
            if cell.provides:
                explanation += f"Provides variables: {', '.join(cell.provides)}\n"
            if cell.requires:
                explanation += f"Requires variables: {', '.join(cell.requires)}\n"

        return explanation

    async def run_stdio(self) -> None:
        """Run the MCP server using stdio transport."""
        logger.info(f"Starting MCP server for {self.notebook_path}")

        async def read_messages() -> AsyncGenerator[Dict[str, Any], None]:
            """Read messages from stdin."""
            while True:
                try:
                    line = await asyncio.to_thread(sys.stdin.readline)
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        message = json.loads(line)
                        yield message
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error reading message: {e}")
                    break

        async def write_message(message: Dict[str, Any]) -> None:
            """Write message to stdout."""
            try:
                json_str = json.dumps(message, separators=(",", ":"))
                print(json_str, flush=True)
            except Exception as e:
                logger.error(f"Error writing message: {e}")

        # Process messages
        async for message in read_messages():
            response = await self.handle_message(message)
            if response:
                await write_message(response)
