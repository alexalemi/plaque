"""Tests for MCP server functionality."""

import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from plaque.mcp.server import MCPServer
from plaque.mcp.resources import ResourceProvider
from plaque.mcp.prompts import PromptProvider
from plaque.mcp.analyzers import (
    CodeQualityAnalyzer,
    DependencyTracker,
    PerformanceAnalyzer,
)
from plaque.cell import Cell, CellType
from plaque.processor import Processor


class TestMCPServer:
    """Test MCP server JSON-RPC functionality."""

    @pytest.fixture
    def mock_processor(self):
        """Create a mock processor with test cells."""
        processor = Mock(spec=Processor)
        processor.cells = [
            Cell(type=CellType.MARKDOWN, content="# Test Notebook", lineno=1),
            Cell(
                type=CellType.CODE,
                content="x = 42\nprint(x)",
                lineno=3,
                counter=1,
                result=42,
                stdout="42\n",
                provides={"x"},
            ),
            Cell(
                type=CellType.CODE,
                content="y = x * 2",
                lineno=6,
                counter=2,
                result=84,
                provides={"y"},
                requires={"x"},
                depends_on={1},
            ),
            Cell(
                type=CellType.CODE,
                content="z = 1/0",
                lineno=8,
                counter=3,
                error="ZeroDivisionError: division by zero",
                stderr="ZeroDivisionError: division by zero",
            ),
        ]
        return processor

    @pytest.fixture
    def mcp_server(self, mock_processor):
        """Create MCP server instance."""
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            notebook_path = Path(f.name)
            server = MCPServer(notebook_path, mock_processor)
            return server

    @pytest.mark.asyncio
    async def test_initialize_request(self, mcp_server):
        """Test initialize request handling."""
        message = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "capabilities": {},
            },
        }

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2025-06-18"
        assert response["result"]["serverInfo"]["name"] == "plaque-mcp"
        assert "capabilities" in response["result"]

    @pytest.mark.asyncio
    async def test_initialized_notification(self, mcp_server):
        """Test initialized notification handling."""
        message = {"jsonrpc": "2.0", "method": "initialized", "params": {}}

        with patch.object(mcp_server, "_refresh_notebook") as mock_refresh:
            response = await mcp_server.handle_message(message)

            assert response is None  # Notifications don't return responses
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_request(self, mcp_server):
        """Test ping request handling."""
        message = {"jsonrpc": "2.0", "id": "2", "method": "ping"}

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "2"
        assert response["result"] == {}

    @pytest.mark.asyncio
    async def test_resources_list(self, mcp_server):
        """Test resources/list request."""
        message = {"jsonrpc": "2.0", "id": "3", "method": "resources/list"}

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "3"
        assert "result" in response
        assert "resources" in response["result"]

        resources = response["result"]["resources"]
        assert len(resources) > 0

        # Check for basic resources
        resource_uris = [r["uri"] for r in resources]
        assert "notebook://cells" in resource_uris
        assert "notebook://state" in resource_uris
        assert "notebook://errors" in resource_uris

    @pytest.mark.asyncio
    async def test_resources_read(self, mcp_server):
        """Test resources/read request."""
        message = {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "resources/read",
            "params": {"uri": "notebook://state"},
        }

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "4"
        assert "result" in response
        assert "contents" in response["result"]

        contents = response["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == "notebook://state"
        assert contents[0]["mimeType"] == "application/json"

    @pytest.mark.asyncio
    async def test_prompts_list(self, mcp_server):
        """Test prompts/list request."""
        message = {"jsonrpc": "2.0", "id": "5", "method": "prompts/list"}

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "5"
        assert "result" in response
        assert "prompts" in response["result"]

        prompts = response["result"]["prompts"]
        assert len(prompts) > 0

        # Check for basic prompts
        prompt_names = [p["name"] for p in prompts]
        assert "analyze_notebook" in prompt_names
        assert "debug_errors" in prompt_names

    @pytest.mark.asyncio
    async def test_prompts_get(self, mcp_server):
        """Test prompts/get request."""
        message = {
            "jsonrpc": "2.0",
            "id": "6",
            "method": "prompts/get",
            "params": {"name": "analyze_notebook", "arguments": {"focus": "quality"}},
        }

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "6"
        assert "result" in response
        assert "description" in response["result"]
        assert "messages" in response["result"]

    @pytest.mark.asyncio
    async def test_tools_list(self, mcp_server):
        """Test tools/list request."""
        message = {"jsonrpc": "2.0", "id": "7", "method": "tools/list"}

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "7"
        assert "result" in response
        assert "tools" in response["result"]

        tools = response["result"]["tools"]
        assert len(tools) > 0

        # Check for basic tools
        tool_names = [t["name"] for t in tools]
        assert "search" in tool_names
        assert "explain" in tool_names

    @pytest.mark.asyncio
    async def test_tools_call_search(self, mcp_server):
        """Test tools/call with search tool."""
        message = {
            "jsonrpc": "2.0",
            "id": "8",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "x"}},
        }

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "8"
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """Test error handling for invalid requests."""
        # Invalid method
        message = {"jsonrpc": "2.0", "id": "9", "method": "invalid/method"}

        response = await mcp_server.handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "9"
        assert "error" in response
        assert response["error"]["code"] == -32601


class TestResourceProvider:
    """Test MCP resource provider."""

    @pytest.fixture
    def mock_processor(self):
        """Create a mock processor with test cells."""
        processor = Mock(spec=Processor)
        processor.cells = [
            Cell(
                type=CellType.CODE,
                content="x = 42",
                lineno=1,
                counter=1,
                result=42,
                provides={"x"},
            ),
            Cell(
                type=CellType.CODE,
                content="y = x * 2",
                lineno=2,
                counter=2,
                result=84,
                provides={"y"},
                requires={"x"},
            ),
        ]
        return processor

    @pytest.fixture
    def resource_provider(self, mock_processor):
        """Create resource provider instance."""
        return ResourceProvider(mock_processor)

    @pytest.mark.asyncio
    async def test_list_resources(self, resource_provider):
        """Test listing all resources."""
        resources = await resource_provider.list_resources()

        assert len(resources) > 0

        # Check basic resources exist
        uris = [r["uri"] for r in resources]
        assert "notebook://cells" in uris
        assert "notebook://state" in uris
        assert "notebook://errors" in uris
        assert "notebook://dependencies" in uris
        assert "notebook://outputs" in uris
        assert "notebook://variables" in uris

        # Check cell-specific resources
        assert "notebook://cell/0" in uris
        assert "notebook://cell/1" in uris
        assert "notebook://cell/0/input" in uris
        assert "notebook://cell/1/output" in uris

    @pytest.mark.asyncio
    async def test_read_cells_resource(self, resource_provider):
        """Test reading cells resource."""
        contents = await resource_provider.read_resource("notebook://cells")

        assert len(contents) == 1
        assert contents[0]["uri"] == "notebook://cells"
        assert contents[0]["mimeType"] == "application/json"

        # Parse the JSON content
        data = json.loads(contents[0]["text"])
        assert "cells" in data
        assert len(data["cells"]) == 2

    @pytest.mark.asyncio
    async def test_read_state_resource(self, resource_provider):
        """Test reading state resource."""
        contents = await resource_provider.read_resource("notebook://state")

        assert len(contents) == 1
        data = json.loads(contents[0]["text"])
        assert "total_cells" in data
        assert "execution_summary" in data

    @pytest.mark.asyncio
    async def test_read_cell_resource(self, resource_provider):
        """Test reading individual cell resource."""
        contents = await resource_provider.read_resource("notebook://cell/0")

        assert len(contents) == 1
        data = json.loads(contents[0]["text"])
        assert data["index"] == 0
        assert data["content"] == "x = 42"

    @pytest.mark.asyncio
    async def test_invalid_resource(self, resource_provider):
        """Test handling of invalid resource URIs."""
        with pytest.raises(ValueError, match="Unknown resource path"):
            await resource_provider.read_resource("notebook://invalid")


class TestCodeQualityAnalyzer:
    """Test code quality analyzer."""

    @pytest.fixture
    def mock_processor(self):
        """Create processor with test cells."""
        processor = Mock(spec=Processor)
        processor.cells = [
            Cell(type=CellType.CODE, content="x = 42", lineno=1),
            Cell(
                type=CellType.CODE, content="eval('2 + 2')", lineno=2
            ),  # Security issue
            Cell(
                type=CellType.CODE, content="password = 'secret123'", lineno=3
            ),  # Security issue
            Cell(
                type=CellType.CODE,
                content="# TODO: fix this later\nprint('test')",
                lineno=4,
            ),  # TODO comment
        ]
        return processor

    @pytest.fixture
    def analyzer(self, mock_processor):
        """Create analyzer instance."""
        return CodeQualityAnalyzer(mock_processor)

    def test_analyze_all(self, analyzer):
        """Test analyzing all cells."""
        issues = analyzer.analyze_all()

        assert len(issues) > 0

        # Check for security issues
        security_issues = [i for i in issues if i.issue_type == "security"]
        assert len(security_issues) >= 2  # eval and password

        # Check for TODO comments
        todo_issues = [i for i in issues if i.issue_type == "todo"]
        assert len(todo_issues) >= 1

    def test_security_detection(self, analyzer):
        """Test security issue detection."""
        issues = analyzer.analyze_all()

        security_issues = [i for i in issues if i.issue_type == "security"]

        # Should detect eval usage
        eval_issues = [i for i in security_issues if "eval" in i.description]
        assert len(eval_issues) > 0

        # Should detect hardcoded credentials
        cred_issues = [i for i in security_issues if "credential" in i.description]
        assert len(cred_issues) > 0


class TestDependencyTracker:
    """Test dependency tracker."""

    @pytest.fixture
    def mock_processor(self):
        """Create processor with dependency test cells."""
        processor = Mock(spec=Processor)
        processor.cells = [
            Cell(type=CellType.CODE, content="x = 42", lineno=1, provides={"x"}),
            Cell(
                type=CellType.CODE,
                content="y = x * 2",
                lineno=2,
                provides={"y"},
                requires={"x"},
            ),
            Cell(
                type=CellType.CODE,
                content="z = undefined_var",
                lineno=3,
                requires={"undefined_var"},
            ),
            Cell(
                type=CellType.CODE,
                content="unused = 123",
                lineno=4,
                provides={"unused"},
            ),
        ]
        return processor

    @pytest.fixture
    def tracker(self, mock_processor):
        """Create tracker instance."""
        return DependencyTracker(mock_processor)

    def test_analyze_dependencies(self, tracker):
        """Test dependency analysis."""
        deps = tracker.analyze_dependencies()

        assert "x" in deps
        assert "y" in deps
        assert "undefined_var" in deps
        assert "unused" in deps

        # Check x is defined and used
        assert len(deps["x"].defined_in) > 0
        assert len(deps["x"].used_in) > 0

        # Check y is defined
        assert len(deps["y"].defined_in) > 0

    def test_find_unused_variables(self, tracker):
        """Test finding unused variables."""
        tracker.analyze_dependencies()
        unused = tracker.find_unused_variables()

        assert "unused" in unused

    def test_find_undefined_variables(self, tracker):
        """Test finding undefined variables."""
        tracker.analyze_dependencies()
        undefined = tracker.find_undefined_variables()

        assert "undefined_var" in undefined


class TestPerformanceAnalyzer:
    """Test performance analyzer."""

    @pytest.fixture
    def mock_processor(self):
        """Create processor with performance test cells."""
        processor = Mock(spec=Processor)
        processor.cells = [
            Cell(
                type=CellType.CODE, content="df.iterrows()", lineno=1
            ),  # Performance issue
            Cell(
                type=CellType.CODE, content="for i in range(len(items)):", lineno=2
            ),  # Performance issue
            Cell(
                type=CellType.CODE,
                content="result = []\nfor item in items:\n    result.append(item)",
                lineno=3,
            ),  # Performance issue
        ]
        return processor

    @pytest.fixture
    def analyzer(self, mock_processor):
        """Create analyzer instance."""
        return PerformanceAnalyzer(mock_processor)

    def test_analyze_performance_issues(self, analyzer):
        """Test performance issue detection."""
        issues = analyzer.analyze_performance_issues()

        assert len(issues) > 0

        # Check for performance issues
        perf_issues = [i for i in issues if i.issue_type == "performance"]
        assert len(perf_issues) > 0

        # Should detect iterrows usage
        iterrows_issues = [i for i in perf_issues if "iterrows" in i.description]
        assert len(iterrows_issues) > 0
