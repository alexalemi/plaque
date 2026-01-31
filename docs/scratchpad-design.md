# Scratchpad Feature Design Document

## Overview

The scratchpad feature allows users and AI agents to execute Python code against a **forked** version of the notebook environment. This enables exploration and inspection of the current state (checking shapes, types, values) without affecting the notebook's execution state.

## Use Cases

1. **AI Agent Exploration**: Claude can inspect variable types, shapes, and values to better understand the notebook state before suggesting code changes.

2. **User Experimentation**: Users can open a side panel to try out code snippets, explore APIs, or debug without adding cells to their notebook.

3. **Live Debugging**: Inspect intermediate values or test transformations without committing them to the notebook.

## Core Concept: Environment Forking

### The Problem
The main notebook maintains persistent state in `Environment.shell.user_ns`. If we execute scratchpad code directly in this namespace:
- New variables would pollute the main namespace
- Side effects would persist
- The notebook state would become inconsistent with the source file

### The Solution: Forked Namespaces
Create a new IPython shell instance with a **shallow copy** of the main namespace:

```python
def fork_environment(main_environment):
    """Create a scratchpad environment forked from the main notebook."""
    scratchpad_shell = InteractiveShell()
    # Shallow copy: new variable assignments are isolated,
    # but shared mutable objects (like DataFrames) can still be read
    scratchpad_shell.user_ns.update(main_environment.shell.user_ns.copy())
    return scratchpad_shell
```

**Trade-offs:**
- ✅ Fast to create (no deep copy needed)
- ✅ Reads from main namespace work perfectly
- ✅ New variable assignments stay in scratchpad
- ⚠️ Mutations to shared mutable objects affect both (acceptable for inspection use case)

For most inspection use cases (`df.shape`, `type(x)`, `model.summary()`), this is ideal.

---

## Architecture

### New Components

```
┌─────────────────────────────────────────────────────────────┐
│                    NotebookHTTPServer                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   Processor     │    │     ScratchpadManager           │ │
│  │   (main nb)     │◄───┤                                 │ │
│  │                 │    │  sessions: Dict[id, Session]    │ │
│  │  ┌───────────┐  │    │                                 │ │
│  │  │Environment│  │    │  ┌───────────────────────────┐  │ │
│  │  │ (main)    │──┼────┼─►│ ScratchpadSession         │  │ │
│  │  │           │  │    │  │  - forked_shell           │  │ │
│  │  │ user_ns   │  │    │  │  - history                │  │ │
│  │  └───────────┘  │    │  │  - created_at             │  │ │
│  └─────────────────┘    │  └───────────────────────────┘  │ │
│                         │                                 │ │
│                         │  ┌───────────────────────────┐  │ │
│                         │  │ ScratchpadSession (2)     │  │ │
│                         │  │  ...                      │  │ │
│                         │  └───────────────────────────┘  │ │
│                         └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
src/plaque/
├── scratchpad.py          # NEW: ScratchpadSession, ScratchpadManager
├── server.py              # MODIFY: Add scratchpad API endpoints
├── environment.py         # MINOR: May need fork helper method
└── formatter.py           # MODIFY: Add scratchpad panel to HTML

src/plaque/static/         # NEW: Static assets directory
├── scratchpad.js          # NEW: Frontend JS for scratchpad UI
└── scratchpad.css         # NEW: Styles for side panel
```

---

## API Design

### REST API Endpoints

All scratchpad endpoints are under `/api/scratchpad/`.

#### 1. Ephemeral Execution (Stateless)

Execute code in a fresh fork that's immediately discarded.

```http
POST /api/scratchpad/execute
Content-Type: application/json

{
  "code": "df.shape"
}
```

**Response:**
```json
{
  "success": true,
  "counter": 1,
  "stdout": "",
  "stderr": "",
  "result": {
    "type": "text/plain",
    "data": "(100, 5)"
  },
  "error": null,
  "execution_time_ms": 12
}
```

#### 2. Create Persistent Session

Create a session that maintains state across multiple executions.

```http
POST /api/scratchpad/session
```

**Response:**
```json
{
  "session_id": "sp_abc123",
  "created_at": 1640000000.123,
  "forked_from_update": 1639999999.456
}
```

#### 3. Execute in Session

```http
POST /api/scratchpad/session/{session_id}/execute
Content-Type: application/json

{
  "code": "subset = df[df['value'] > 0]\nsubset.shape"
}
```

**Response:** Same format as ephemeral execution.

#### 4. List Session Variables

```http
GET /api/scratchpad/session/{session_id}/variables
```

**Response:**
```json
{
  "session_id": "sp_abc123",
  "variables": [
    {"name": "df", "type": "DataFrame", "from_notebook": true},
    {"name": "subset", "type": "DataFrame", "from_notebook": false},
    {"name": "x", "type": "int", "from_notebook": false}
  ]
}
```

#### 5. Reset Session (Re-fork)

```http
POST /api/scratchpad/session/{session_id}/reset
```

Re-forks from the current notebook state, discarding scratchpad-specific variables.

#### 6. Delete Session

```http
DELETE /api/scratchpad/session/{session_id}
```

#### 7. List Active Sessions

```http
GET /api/scratchpad/sessions
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "sp_abc123",
      "created_at": 1640000000.123,
      "execution_count": 5,
      "last_execution": 1640000100.456
    }
  ]
}
```

---

## Frontend UI Design

### Side Panel Component

```
┌─────────────────────────────────────────┬────────────────────────┐
│                                         │   ⚙️ Scratchpad        │
│                                         ├────────────────────────┤
│                                         │ >>> df.shape           │
│        Main Notebook Content            │ (100, 5)               │
│                                         │                        │
│                                         │ >>> df.columns.tolist()│
│                                         │ ['a', 'b', 'c', 'd']   │
│                                         │                        │
│                                         │ >>> type(model)        │
│                                         │ <class 'sklearn...'>   │
│                                         ├────────────────────────┤
│                                         │ ┌──────────────────┐   │
│                                         │ │ x = df.head()    │   │
│                                         │ │                  │   │
│                                         │ └──────────────────┘   │
│                                         │ [Run] [Reset] [Clear]  │
└─────────────────────────────────────────┴────────────────────────┘
```

### UI Features

1. **Toggle Button**: Keyboard shortcut (Ctrl+`) or button to open/close panel
2. **Code Input**: Multi-line textarea with basic syntax highlighting
3. **Output Area**: Scrollable history of executed commands and results
4. **Action Buttons**:
   - **Run** (or Ctrl+Enter): Execute current code
   - **Reset**: Re-fork from notebook state
   - **Clear**: Clear output history
5. **Session Indicator**: Shows if using persistent session vs ephemeral
6. **Resizable Panel**: Drag to resize width

### JavaScript Implementation Sketch

```javascript
class ScratchpadUI {
  constructor() {
    this.sessionId = null;  // null = ephemeral mode
    this.history = [];
  }

  async execute(code) {
    const endpoint = this.sessionId
      ? `/api/scratchpad/session/${this.sessionId}/execute`
      : '/api/scratchpad/execute';

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code})
    });

    const result = await response.json();
    this.addToHistory(code, result);
    return result;
  }

  async reset() {
    if (this.sessionId) {
      await fetch(`/api/scratchpad/session/${this.sessionId}/reset`, {
        method: 'POST'
      });
    }
    // For ephemeral mode, reset is a no-op (each execution is fresh)
  }
}
```

---

## MCP Server Integration (Optional)

For tighter Claude Code integration, we can expose scratchpad as an MCP server.

### MCP Tools

```yaml
tools:
  - name: scratchpad_execute
    description: Execute Python code in a forked notebook environment for inspection
    inputSchema:
      type: object
      properties:
        code:
          type: string
          description: Python code to execute
      required: [code]

  - name: scratchpad_inspect
    description: Inspect a variable's type, shape, and preview
    inputSchema:
      type: object
      properties:
        variable:
          type: string
          description: Variable name to inspect
      required: [variable]

  - name: scratchpad_list_variables
    description: List all variables in the notebook namespace
    inputSchema:
      type: object
      properties: {}
```

### MCP Server Architecture

Option A: **Wrap REST API**
- MCP server makes HTTP requests to the running plaque server
- Simple, but requires plaque server to be running

Option B: **Direct Integration**
- MCP server directly imports and uses `ScratchpadManager`
- More tightly coupled, but no HTTP overhead

### Launch Pattern

```bash
# Option A: Separate process
plaque serve notebook.py --port 5000 &
plaque mcp --port 5000  # Connects to running server

# Option B: Combined
plaque serve notebook.py --port 5000 --mcp  # Enables MCP server too
```

---

## Implementation Plan

### Phase 1: Backend Core (scratchpad.py)

**Priority: High**

```python
# src/plaque/scratchpad.py

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from IPython.core.interactiveshell import InteractiveShell

@dataclass
class ExecutionResult:
    success: bool
    counter: int
    stdout: str
    stderr: str
    result: Any  # Will be formatted by api_formatter
    error: Optional[str]
    execution_time_ms: float

@dataclass
class ScratchpadSession:
    session_id: str
    shell: InteractiveShell
    created_at: float
    forked_from_update: float
    execution_count: int = 0
    last_execution: Optional[float] = None
    history: List[tuple] = field(default_factory=list)  # (code, result) pairs

    def execute(self, code: str) -> ExecutionResult:
        """Execute code in this session's forked environment."""
        # Similar to Environment.execute_cell but simpler
        ...

    def get_variables(self) -> List[dict]:
        """List variables with type info."""
        ...

    def reset(self, main_environment):
        """Re-fork from main environment."""
        ...

class ScratchpadManager:
    def __init__(self, main_environment):
        self.main_environment = main_environment
        self.sessions: Dict[str, ScratchpadSession] = {}
        self.max_sessions = 10  # Limit concurrent sessions
        self.session_timeout = 3600  # 1 hour

    def create_session(self) -> ScratchpadSession:
        """Create a new forked session."""
        ...

    def execute_ephemeral(self, code: str) -> ExecutionResult:
        """Execute in a fresh fork (no persistent session)."""
        ...

    def get_session(self, session_id: str) -> Optional[ScratchpadSession]:
        ...

    def delete_session(self, session_id: str) -> bool:
        ...

    def cleanup_expired(self):
        """Remove sessions older than timeout."""
        ...
```

### Phase 2: REST API Endpoints

**Priority: High**

Add to `server.py`:

```python
def handle_scratchpad_api(self, path, method, body):
    if path == "/api/scratchpad/execute" and method == "POST":
        return self.scratchpad_execute_ephemeral(body)
    elif path == "/api/scratchpad/session" and method == "POST":
        return self.scratchpad_create_session()
    elif path.startswith("/api/scratchpad/session/"):
        # Parse session_id and sub-path
        ...
```

### Phase 3: Frontend UI

**Priority: Medium**

1. Create `src/plaque/static/` directory
2. Add `scratchpad.js` with UI logic
3. Add `scratchpad.css` with styling
4. Modify `formatter.py` to inject scratchpad panel HTML/CSS/JS
5. Add static file serving to `server.py`

### Phase 4: MCP Server (Optional)

**Priority: Low**

1. Create `src/plaque/mcp_server.py`
2. Define MCP tools schema
3. Implement tool handlers
4. Add CLI command `plaque mcp`

---

## Security Considerations

1. **No Network Exposure**: By default, scratchpad only available on localhost
2. **Session Limits**: Cap number of concurrent sessions to prevent memory exhaustion
3. **Timeout**: Auto-expire sessions after inactivity
4. **Code Execution**: Same security model as notebook cells (user's own code)

---

## Testing Strategy

### Unit Tests
- `test_scratchpad_session_isolation.py`: Verify namespace isolation
- `test_scratchpad_execution.py`: Verify code execution and result capture
- `test_scratchpad_manager.py`: Session lifecycle, cleanup

### Integration Tests
- `test_scratchpad_api.py`: HTTP endpoint tests
- `test_scratchpad_ui.py`: Browser-based UI tests (optional)

### Example Test Cases
```python
def test_scratchpad_isolation():
    """Scratchpad writes don't affect main namespace."""
    main_env = Environment()
    main_env.shell.user_ns['x'] = 10

    manager = ScratchpadManager(main_env)
    result = manager.execute_ephemeral("x = 999; x")

    assert result.result == 999  # Scratchpad saw new value
    assert main_env.shell.user_ns['x'] == 10  # Main unchanged

def test_scratchpad_reads_main():
    """Scratchpad can read main namespace."""
    main_env = Environment()
    main_env.shell.user_ns['df'] = pd.DataFrame({'a': [1,2,3]})

    manager = ScratchpadManager(main_env)
    result = manager.execute_ephemeral("df.shape")

    assert "(3, 1)" in str(result.result)
```

---

## Open Questions

1. **Session Persistence**: Should sessions survive server restart? (Probably no - they're ephemeral by design)

2. **Multi-User**: If server is exposed on network, should each client get isolated sessions? (Yes, via session IDs)

3. **Mutation Warning**: Should we detect and warn about mutations to shared mutable objects? (Nice to have, but complex)

4. **Sync with Notebook**: When notebook re-executes, should scratchpad sessions auto-refresh? (Probably yes, or at least offer refresh)

5. **History Persistence**: Should scratchpad command history persist to a file? (Nice to have for UX)

---

## Success Metrics

1. **Latency**: Ephemeral execution < 100ms for simple commands
2. **Memory**: Each session adds < 50MB overhead (mostly namespace copy)
3. **Reliability**: 99%+ success rate for read-only inspection commands
4. **UX**: Panel opens in < 200ms, feels responsive

---

## Detailed Implementation Reference

### Key Files and How They Interact

Based on codebase analysis:

```
processor.py (Processor)
    └── environment.py (Environment)
            └── IPython.InteractiveShell
                    └── shell.user_ns (dict) ← THIS IS THE NAMESPACE TO FORK

server.py (NotebookHTTPServer)
    ├── self.processor → reference to Processor
    ├── self.current_cells → List[Cell] after execution
    └── NotebookRequestHandler
            └── handle_api_request() ← ADD SCRATCHPAD ENDPOINTS HERE

api_formatter.py
    └── format_result() ← REUSE FOR SCRATCHPAD RESULTS
```

### Environment Forking Strategy

The `Environment` class in `environment.py:154-200` shows how IPython is set up:

```python
class Environment:
    def __init__(self):
        self.shell = InteractiveShell()
        self.shell.ast_node_interactivity = "last_expr"
        self.shell.autoawait = True
        # ... display hook setup ...
        self.shell.user_ns["__name__"] = "__main__"
        self.counter = 0
```

**Forking approach:**

```python
def create_forked_environment(main_env: Environment) -> Environment:
    """Create a new Environment that starts with a copy of main_env's namespace."""
    forked = Environment()  # Fresh IPython shell

    # Copy the namespace (shallow copy is sufficient for inspection)
    forked.shell.user_ns.update(main_env.shell.user_ns.copy())

    # Start counter at 0 for scratchpad
    forked.counter = 0

    return forked
```

**Why this works:**
- New `InteractiveShell` instance = isolated execution
- Shallow copy of `user_ns` = can read all main namespace variables
- New assignments in scratchpad don't affect main namespace
- Main namespace objects are shared (reads work, in-place mutations would propagate)

### Adding Scratchpad Endpoints to Server

In `server.py`, the pattern for API endpoints is in `handle_api_request()` (lines 248-391).
Add scratchpad routes following the same pattern:

```python
# In do_GET:
elif self.path.startswith("/api/scratchpad"):
    self.handle_scratchpad_api()

# In do_POST:
def do_POST(self):
    if self.path.startswith("/api/scratchpad"):
        self.handle_scratchpad_post()

def handle_scratchpad_post(self):
    content_length = int(self.headers.get('Content-Length', 0))
    body = self.rfile.read(content_length).decode('utf-8')
    data = json.loads(body)

    if self.path == "/api/scratchpad/execute":
        result = server_instance.scratchpad_manager.execute_ephemeral(data['code'])
        self.send_json_response(result.to_dict())
    # ... other endpoints ...
```

### Result Formatting

Reuse `api_formatter.format_result()` for scratchpad results:

```python
from .api_formatter import format_result

def execute_and_format(self, code: str) -> dict:
    # Execute in forked environment
    result = self.forked_env.execute_code(code)

    return {
        "success": result.error is None,
        "counter": result.counter,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": result.error,
        "result": format_result(result.value, self.image_dir, result.counter),
        "execution_time_ms": result.execution_time_ms,
    }
```

### Frontend Integration

The HTML is generated in `formatter.py`. Inject scratchpad panel by adding to the template:

```html
<!-- Scratchpad Panel -->
<div id="scratchpad-panel" class="scratchpad-hidden">
    <div class="scratchpad-header">
        <span>Scratchpad</span>
        <button id="scratchpad-close">×</button>
    </div>
    <div id="scratchpad-output"></div>
    <div class="scratchpad-input-area">
        <textarea id="scratchpad-input" placeholder=">>> "></textarea>
        <div class="scratchpad-buttons">
            <button id="scratchpad-run">Run (Ctrl+Enter)</button>
            <button id="scratchpad-reset">Reset</button>
        </div>
    </div>
</div>
<button id="scratchpad-toggle" title="Toggle Scratchpad (Ctrl+`)">⚡</button>
```

Add to the auto-reload script injection in `_inject_auto_reload_script()`:

```javascript
// Scratchpad functionality
const scratchpad = {
    sessionId: null,
    execute: async function(code) {
        const endpoint = this.sessionId
            ? `/api/scratchpad/session/${this.sessionId}/execute`
            : '/api/scratchpad/execute';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code})
        });
        return response.json();
    }
};
```

### MCP Server Option

For Claude Code integration, an MCP server can wrap the REST API:

```python
# src/plaque/mcp_server.py
from mcp.server import Server
from mcp.types import Tool

server = Server("plaque-scratchpad")

@server.tool("scratchpad_execute")
async def execute_scratchpad(code: str) -> str:
    """Execute Python code in a forked notebook environment."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://localhost:{PLAQUE_PORT}/api/scratchpad/execute",
            json={"code": code}
        ) as resp:
            result = await resp.json()
            return json.dumps(result, indent=2)
```

CLI integration:
```bash
plaque serve notebook.py --mcp  # Starts plaque server + MCP server
```

---

## Recommended Implementation Order

1. **Phase 1: Core Backend** (high impact, foundational)
   - Create `scratchpad.py` with `ScratchpadSession` and `ScratchpadManager`
   - Add `execute_ephemeral()` that creates a forked env, runs code, returns result
   - Unit tests for namespace isolation

2. **Phase 2: REST API** (enables both Claude and UI)
   - Add POST `/api/scratchpad/execute` endpoint to server
   - Add session management endpoints
   - Integration tests

3. **Phase 3: Frontend UI** (user-facing)
   - Add HTML panel to formatter template
   - Add JavaScript for API calls and UI interactions
   - Add CSS styling

4. **Phase 4: MCP Server** (optional, for tighter Claude integration)
   - Wrap REST API in MCP server
   - Add CLI flag `--mcp`
