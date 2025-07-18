#!/usr/bin/env python3
"""
Simple MCP test client to demonstrate interaction with the Plaque MCP server.
"""

import json
import subprocess
import sys
import time
from typing import Dict, Any, Optional


class MCPTestClient:
    """Simple MCP client for testing purposes."""

    def __init__(self, notebook_path: str):
        self.notebook_path = notebook_path
        self.process = None
        self.request_id = 0

    def start_server(self):
        """Start the MCP server process."""
        cmd = [sys.executable, "-m", "plaque.cli", "mcp", self.notebook_path]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
        )
        # Give the server time to start
        time.sleep(1)

    def stop_server(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait()

    def send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        self.request_id += 1

        request = {"jsonrpc": "2.0", "id": str(self.request_id), "method": method}

        if params:
            request["params"] = params

        # Send request
        request_json = json.dumps(request)
        print(f"→ {request_json}")

        self.process.stdin.write(request_json + "\n")
        self.process.stdin.flush()

        # Read response
        response_line = self.process.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            print(f"← {json.dumps(response, indent=2)}")
            return response
        else:
            print("← No response received")
            return {}

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a notification (no response expected)."""
        notification = {"jsonrpc": "2.0", "method": method}

        if params:
            notification["params"] = params

        # Send notification
        notification_json = json.dumps(notification)
        print(f"→ {notification_json}")

        self.process.stdin.write(notification_json + "\n")
        self.process.stdin.flush()

    def run_test_sequence(self):
        """Run a sequence of test requests."""
        print("=== MCP Server Test Sequence ===\n")

        # 1. Initialize
        print("1. Initializing connection...")
        self.send_request(
            "initialize",
            {
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "capabilities": {},
            },
        )

        # 2. Send initialized notification
        print("\n2. Sending initialized notification...")
        self.send_notification("initialized", {})

        # 3. Test ping
        print("\n3. Testing ping...")
        self.send_request("ping")

        # 4. List resources
        print("\n4. Listing resources...")
        self.send_request("resources/list")

        # 5. Read notebook state
        print("\n5. Reading notebook state...")
        self.send_request("resources/read", {"uri": "notebook://state"})

        # 6. Read errors
        print("\n6. Reading errors...")
        self.send_request("resources/read", {"uri": "notebook://errors"})

        # 7. List prompts
        print("\n7. Listing prompts...")
        self.send_request("prompts/list")

        # 8. Get analysis prompt
        print("\n8. Getting analysis prompt...")
        self.send_request("prompts/get", {"name": "debug_errors", "arguments": {}})

        # 9. List tools
        print("\n9. Listing tools...")
        self.send_request("tools/list")

        # 10. Use search tool
        print("\n10. Using search tool...")
        self.send_request(
            "tools/call", {"name": "search", "arguments": {"query": "pandas"}}
        )

        print("\n=== Test Complete ===")


def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python mcp_test_client.py <notebook_path>")
        sys.exit(1)

    notebook_path = sys.argv[1]
    client = MCPTestClient(notebook_path)

    try:
        print(f"Starting MCP server for: {notebook_path}")
        client.start_server()

        # Run test sequence
        client.run_test_sequence()

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        # Print any stderr output
        if client.process and client.process.stderr:
            stderr_output = client.process.stderr.read()
            if stderr_output:
                print(f"Server stderr: {stderr_output}")
    finally:
        client.stop_server()


if __name__ == "__main__":
    main()
