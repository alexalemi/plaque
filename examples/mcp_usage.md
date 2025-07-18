# MCP Server Usage Guide

The Plaque MCP (Model Context Protocol) server provides read-only access to notebook state and analysis for AI agents and tools.

## Starting the MCP Server

```bash
# Start MCP server for a notebook
plaque mcp my_notebook.py

# Start with verbose logging
plaque mcp my_notebook.py --verbose
```

The server uses stdio transport and communicates via JSON-RPC 2.0 messages.

## MCP Capabilities

### Resources (Read-only data access)

The MCP server provides several resources for accessing notebook data:

#### Overall Notebook Resources
- `notebook://cells` - All cells with complete metadata
- `notebook://state` - Overall notebook status and statistics
- `notebook://errors` - Summary of all errors
- `notebook://dependencies` - Variable dependency graph
- `notebook://outputs` - All cell outputs (text, images, dataframes)
- `notebook://variables` - Current variable state

#### Individual Cell Resources
- `notebook://cell/{index}` - Complete cell details
- `notebook://cell/{index}/input` - Just the source code
- `notebook://cell/{index}/output` - Just the execution results

### Prompts (Analysis workflows)

The server provides analysis prompts for common agent workflows:

- `analyze_notebook` - Comprehensive code quality analysis
- `debug_errors` - Error diagnosis and suggestions
- `trace_dependencies` - Variable flow analysis
- `performance_review` - Performance bottleneck identification
- `security_audit` - Security issue detection

### Tools (Safe operations)

Limited set of safe, read-only tools:

- `search` - Search cells by content
- `explain` - Explain code segments

## Example MCP Client Usage

Here's how an AI agent might interact with the MCP server:

### 1. Initialize Connection

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "initialize",
  "params": {
    "clientInfo": {"name": "my-agent", "version": "1.0"},
    "capabilities": {}
  }
}
```

### 2. Get Notebook State

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "resources/read",
  "params": {"uri": "notebook://state"}
}
```

### 3. Analyze Errors

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "resources/read",
  "params": {"uri": "notebook://errors"}
}
```

### 4. Get Analysis Prompt

```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "prompts/get",
  "params": {
    "name": "debug_errors",
    "arguments": {}
  }
}
```

### 5. Search for Specific Code

```json
{
  "jsonrpc": "2.0",
  "id": "5",
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "pandas"}
  }
}
```

## Integration with AI Tools

The MCP server is designed to work with various AI tools and agents:

### Claude Desktop
Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "plaque": {
      "command": "plaque",
      "args": ["mcp", "path/to/notebook.py"]
    }
  }
}
```

### Custom Agents
Use any MCP-compatible client library to connect to the server via stdio transport.

## Benefits for AI Agents

1. **Rich Context**: Access to complete notebook state, dependencies, and outputs
2. **Structured Data**: JSON-formatted data perfect for AI analysis
3. **Analysis Prompts**: Pre-built prompts for common analysis tasks
4. **Error Insights**: Detailed error information with context
5. **Performance Analysis**: Automated detection of performance issues
6. **Security Scanning**: Built-in security vulnerability detection

## File-First Philosophy

The MCP server is **read-only** - it doesn't modify your notebook files. All changes must be made by editing the source file directly. This preserves Plaque's file-first philosophy while providing rich inspection capabilities for AI agents.

When you edit the notebook file, the server automatically detects changes and updates its internal state, providing fresh data to connected agents.

## Advanced Features

### Code Quality Analysis
The server includes built-in analyzers for:
- Code style issues
- Security vulnerabilities
- Performance bottlenecks
- Unused imports
- Complex functions
- TODO/FIXME comments

### Dependency Tracking
Advanced dependency analysis including:
- Variable definitions and usage
- Cell dependencies
- Circular dependency detection
- Unused variable identification

### Performance Insights
Automated detection of:
- Inefficient loops
- Poor pandas usage patterns
- Memory-intensive operations
- Vectorization opportunities

This makes the MCP server a powerful tool for AI-assisted code review and optimization.