"""HTTP server for live notebook serving with auto-reload."""

import http.server
import socketserver
import tempfile
import shutil
import os
import webbrowser
from pathlib import Path
from typing import Callable, Optional

import click

from .watcher import FileWatcher


class NotebookHTTPServer:
    """HTTP server for serving notebooks with live reload."""
    
    def __init__(self, notebook_path: Path, port: int = 5000):
        self.notebook_path = notebook_path
        self.port = port
        self.temp_dir: Optional[str] = None
        self.watcher: Optional[FileWatcher] = None
        self.html_path: Optional[Path] = None
        
    def start(self, regenerate_callback: Callable[[str], str], open_browser: bool = False):
        """Start the HTTP server with file watching."""
        self.temp_dir = None
        self.watcher = None
        
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="plaque_")
            temp_path = Path(self.temp_dir)
            self.html_path = temp_path / f"{self.notebook_path.stem}.html"
            
            def regenerate_html():
                """Regenerate HTML when file changes."""
                try:
                    html_content = regenerate_callback(str(self.notebook_path))
                    with open(self.html_path, 'w') as f:
                        f.write(html_content)
                    click.echo(f"Regenerated: {self.notebook_path.name}")
                except Exception as e:
                    click.echo(f"Error regenerating {self.notebook_path}: {e}", err=True)
            
            # Initial generation
            regenerate_html()
            
            # Set up file watcher
            self.watcher = FileWatcher(str(self.notebook_path), lambda path: regenerate_html())
            self.watcher.start()
            
            # Start HTTP server
            original_cwd = os.getcwd()
            os.chdir(temp_path)
            
            try:
                handler = http.server.SimpleHTTPRequestHandler
                
                with socketserver.TCPServer(("", self.port), handler) as httpd:
                    url = f"http://localhost:{self.port}/{self.html_path.name}"
                    
                    click.echo(f"Serving {self.notebook_path.name} at {url}")
                    click.echo("Press Ctrl+C to stop")
                    
                    if open_browser:
                        webbrowser.open(url)
                    
                    try:
                        httpd.serve_forever()
                    except KeyboardInterrupt:
                        click.echo("\nStopping server...")
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


def start_notebook_server(notebook_path: Path, port: int, regenerate_callback: Callable[[str], str], open_browser: bool = False):
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