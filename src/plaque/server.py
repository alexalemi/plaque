"""HTTP server for live notebook serving with auto-reload."""

import http.server
import socketserver
import tempfile
import shutil
import os
import webbrowser
import time
import json
from pathlib import Path
from typing import Callable, Optional

import click

from .watcher import FileWatcher
from .api_formatter import cell_to_json, cells_to_json, notebook_state_to_json


class ReusableTCPServer(socketserver.TCPServer):
    """TCPServer that allows address reuse."""

    allow_reuse_address = True


class NotebookHTTPServer:
    """HTTP server for serving notebooks with live reload."""

    def __init__(self, notebook_path: Path, port: int = 5000, bind: str = "localhost"):
        self.notebook_path = notebook_path
        self.port = port
        self.bind = bind
        self.temp_dir: Optional[str] = None
        self.watcher: Optional[FileWatcher] = None
        self.html_path: Optional[Path] = None
        self.last_update: float = time.time()
        self.processor = None  # Will be set by the caller
        self.current_cells = []  # Current cell state

    def start(
        self,
        regenerate_callback: Callable[[str, Optional[Path]], str],
        open_browser: bool = False,
        processor=None,
    ):
        """Start the HTTP server with file watching."""
        self.temp_dir = None
        self.watcher = None
        self.processor = processor

        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="plaque_")
            temp_path = Path(self.temp_dir)
            self.html_path = temp_path / "index.html"

            # Create images subdirectory
            images_dir = temp_path / "images"
            images_dir.mkdir(exist_ok=True)

            def regenerate_html():
                """Regenerate HTML when file changes."""
                try:
                    html_content = regenerate_callback(
                        str(self.notebook_path), images_dir
                    )

                    # Get the current cells AFTER processing
                    if self.processor and hasattr(self.processor, "cells"):
                        self.current_cells = self.processor.cells

                    # Inject auto-reload JavaScript
                    html_content = self._inject_auto_reload_script(html_content)
                    with open(self.html_path, "w") as f:
                        f.write(html_content)
                    self.last_update = time.time()
                    click.echo(f"Regenerated: {self.notebook_path.name}")
                except Exception as e:
                    click.echo(
                        f"Error regenerating {self.notebook_path}: {e}", err=True
                    )

            # Initial generation
            regenerate_html()

            # Set up file watcher
            self.watcher = FileWatcher(
                str(self.notebook_path), lambda path: regenerate_html()
            )
            self.watcher.start()

            # Start HTTP server
            original_cwd = os.getcwd()
            os.chdir(temp_path)

            try:
                # Create custom handler for auto-reload functionality
                handler_class = self._create_request_handler()

                with ReusableTCPServer((self.bind, self.port), handler_class) as httpd:
                    # Use the bind address in the URL, but show localhost for 0.0.0.0
                    display_host = "localhost" if self.bind == "0.0.0.0" else self.bind
                    url = f"http://{display_host}:{self.port}/"

                    click.echo(f"Serving {self.notebook_path.name} at {url}")
                    click.echo("Press Ctrl+C to stop")

                    if open_browser:
                        webbrowser.open(url)

                    httpd.serve_forever()
            finally:
                # Restore original working directory
                os.chdir(original_cwd)

        except ImportError as e:
            click.echo(f"Server dependencies not available: {e}", err=True)
            raise
        except Exception as e:
            click.echo(f"Error starting server: {e}", err=True)
            raise
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up server resources."""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def _inject_auto_reload_script(self, html_content: str) -> str:
        """Inject auto-reload JavaScript into HTML content."""
        auto_reload_script = """
<script>
(function() {
    let lastUpdate = Date.now();
    
    function checkForUpdates() {
        fetch('/reload_check')
            .then(response => response.json())
            .then(data => {
                if (data.last_update > lastUpdate) {
                    location.reload();
                }
            })
            .catch(err => {
                // Silently ignore errors (server might be restarting)
            });
    }
    
    // Check for updates every 1 second
    setInterval(checkForUpdates, 1000);
})();
</script>"""

        # Inject the script before the closing </body> tag
        if "</body>" in html_content:
            return html_content.replace("</body>", f"{auto_reload_script}\n</body>")
        else:
            # If no </body> tag, append to the end
            return html_content + auto_reload_script

    def _create_request_handler(self):
        """Create a custom HTTP request handler with auto-reload endpoint."""
        server_instance = self

        class NotebookRequestHandler(http.server.SimpleHTTPRequestHandler):
            def send_json_response(self, data: dict, status: int = 200):
                """Helper method to send JSON responses."""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache")
                # CORS headers for agent access
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

            def do_OPTIONS(self):
                """Handle preflight CORS requests."""
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def do_GET(self):
                # API endpoints
                if self.path.startswith("/api/"):
                    self.handle_api_request()
                elif self.path == "/reload_check":
                    # Serve the reload check endpoint
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()

                    response = {
                        "last_update": int(
                            server_instance.last_update * 1000
                        )  # Convert to milliseconds
                    }
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                elif self.path.startswith("/images/"):
                    # Serve images from the images directory
                    image_filename = self.path[8:]  # Remove "/images/" prefix
                    image_path = (
                        Path(server_instance.temp_dir) / "images" / image_filename
                    )

                    if image_path.exists() and image_path.is_file():
                        # Determine content type based on file extension
                        if image_filename.endswith(".png"):
                            content_type = "image/png"
                        elif image_filename.endswith((".jpg", ".jpeg")):
                            content_type = "image/jpeg"
                        elif image_filename.endswith(".svg"):
                            content_type = "image/svg+xml"
                        else:
                            content_type = "application/octet-stream"

                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.send_header(
                            "Cache-Control", "max-age=3600"
                        )  # Cache for 1 hour
                        self.end_headers()

                        with open(image_path, "rb") as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_error(404, "Image not found")
                else:
                    # Use the default handler for all other requests
                    super().do_GET()

            def handle_api_request(self):
                """Handle API requests for agent interoperability."""
                path_parts = self.path.split("/")

                # Get current cells and image directory
                cells = server_instance.current_cells
                image_dir = (
                    Path(server_instance.temp_dir) / "images"
                    if server_instance.temp_dir
                    else None
                )

                try:
                    # /api/cells - List all cells
                    if self.path == "/api/cells":
                        cell_list = []
                        for i, cell in enumerate(cells):
                            cell_info = {
                                "index": i,
                                "type": "code" if cell.type.value == 1 else "markdown",
                                "lineno": cell.lineno,
                                "is_code": cell.is_code,
                                "has_error": bool(cell.error),
                                "execution_count": cell.counter
                                if cell.is_code
                                else None,
                            }
                            cell_list.append(cell_info)
                        self.send_json_response({"cells": cell_list})

                    # /api/cell/{index} - Get specific cell details
                    elif self.path.startswith("/api/cell/") and len(path_parts) == 4:
                        try:
                            index = int(path_parts[3])
                            if 0 <= index < len(cells):
                                cell_data = cell_to_json(cells[index], index, image_dir)
                                self.send_json_response(cell_data)
                            else:
                                self.send_json_response(
                                    {"error": "Cell index out of range"}, 404
                                )
                        except ValueError:
                            self.send_json_response(
                                {"error": "Invalid cell index"}, 400
                            )

                    # /api/cell/{index}/input - Get only input
                    elif self.path.startswith("/api/cell/") and self.path.endswith(
                        "/input"
                    ):
                        try:
                            index = int(path_parts[3])
                            if 0 <= index < len(cells):
                                self.send_json_response(
                                    {"index": index, "content": cells[index].content}
                                )
                            else:
                                self.send_json_response(
                                    {"error": "Cell index out of range"}, 404
                                )
                        except ValueError:
                            self.send_json_response(
                                {"error": "Invalid cell index"}, 400
                            )

                    # /api/cell/{index}/output - Get only output
                    elif self.path.startswith("/api/cell/") and self.path.endswith(
                        "/output"
                    ):
                        try:
                            index = int(path_parts[3])
                            if 0 <= index < len(cells):
                                cell = cells[index]
                                output_data = {
                                    "index": index,
                                    "counter": cell.counter,
                                    "error": cell.error,
                                    "stdout": cell.stdout,
                                    "stderr": cell.stderr,
                                }
                                if cell.result is not None:
                                    from .api_formatter import format_result

                                    output_data["result"] = format_result(
                                        cell.result, image_dir
                                    )
                                else:
                                    output_data["result"] = None
                                self.send_json_response(output_data)
                            else:
                                self.send_json_response(
                                    {"error": "Cell index out of range"}, 404
                                )
                        except ValueError:
                            self.send_json_response(
                                {"error": "Invalid cell index"}, 400
                            )

                    # /api/notebook/state - Get notebook state
                    elif self.path == "/api/notebook/state":
                        state = notebook_state_to_json(
                            cells, server_instance.last_update
                        )
                        self.send_json_response(state)

                    # /api/search - Search cells by content
                    elif self.path.startswith("/api/search"):
                        from urllib.parse import urlparse, parse_qs

                        query_components = parse_qs(urlparse(self.path).query)
                        search_query = query_components.get("q", [""])[0].lower()

                        if search_query:
                            matching_cells = []
                            for i, cell in enumerate(cells):
                                if search_query in cell.content.lower():
                                    matching_cells.append(
                                        {
                                            "index": i,
                                            "type": "code"
                                            if cell.type.value == 1
                                            else "markdown",
                                            "lineno": cell.lineno,
                                            "preview": cell.content[:100] + "..."
                                            if len(cell.content) > 100
                                            else cell.content,
                                        }
                                    )
                            self.send_json_response(
                                {"query": search_query, "results": matching_cells}
                            )
                        else:
                            self.send_json_response(
                                {"error": "Missing search query parameter 'q'"}, 400
                            )

                    else:
                        self.send_json_response({"error": "Unknown API endpoint"}, 404)

                except Exception as e:
                    self.send_json_response({"error": str(e)}, 500)

            def log_message(self, format, *args):
                # Suppress log messages for reload_check and API requests
                if args and (
                    "/reload_check" not in str(args[0]) and "/api/" not in str(args[0])
                ):
                    super().log_message(format, *args)

        return NotebookRequestHandler


def start_notebook_server(
    notebook_path: Path,
    port: int,
    bind: str = "localhost",
    regenerate_callback: Callable[[str, Optional[Path]], str] = None,
    open_browser: bool = False,
    processor=None,
):
    """
    Convenience function to start a notebook server.

    Args:
        notebook_path: Path to the notebook file
        port: Port to serve on
        bind: Host/IP to bind to (default: localhost)
        regenerate_callback: Function that takes a file path and returns HTML content
        open_browser: Whether to open browser automatically
    """
    server = NotebookHTTPServer(notebook_path, port, bind)
    server.start(regenerate_callback, open_browser, processor)
