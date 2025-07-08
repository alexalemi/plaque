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


class ReusableTCPServer(socketserver.TCPServer):
    """TCPServer that allows address reuse."""

    allow_reuse_address = True


class NotebookHTTPServer:
    """HTTP server for serving notebooks with live reload."""

    def __init__(self, notebook_path: Path, port: int = 5000):
        self.notebook_path = notebook_path
        self.port = port
        self.temp_dir: Optional[str] = None
        self.watcher: Optional[FileWatcher] = None
        self.html_path: Optional[Path] = None
        self.last_update: float = time.time()

    def start(
        self, regenerate_callback: Callable[[str], str], open_browser: bool = False
    ):
        """Start the HTTP server with file watching."""
        self.temp_dir = None
        self.watcher = None

        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="plaque_")
            temp_path = Path(self.temp_dir)
            self.html_path = temp_path / "index.html"

            def regenerate_html():
                """Regenerate HTML when file changes."""
                try:
                    html_content = regenerate_callback(str(self.notebook_path))
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

                with ReusableTCPServer(("", self.port), handler_class) as httpd:
                    url = f"http://localhost:{self.port}/"

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
            def do_GET(self):
                if self.path == "/reload_check":
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
                else:
                    # Use the default handler for all other requests
                    super().do_GET()

            def log_message(self, format, *args):
                # Suppress log messages for reload_check requests
                if args and "/reload_check" not in str(args[0]):
                    super().log_message(format, *args)

        return NotebookRequestHandler


def start_notebook_server(
    notebook_path: Path,
    port: int,
    regenerate_callback: Callable[[str], str],
    open_browser: bool = False,
):
    """
    Convenience function to start a notebook server.

    Args:
        notebook_path: Path to the notebook file
        port: Port to serve on
        regenerate_callback: Function that takes a file path and returns HTML content
        open_browser: Whether to open browser automatically
    """
    server = NotebookHTTPServer(notebook_path, port)
    server.start(regenerate_callback, open_browser)
