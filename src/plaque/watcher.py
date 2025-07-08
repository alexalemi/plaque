"""File watcher for live updates."""

import time
import threading
from typing import Callable, Optional
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class NotebookFileHandler(FileSystemEventHandler):
    """Handler for notebook file changes."""
    
    def __init__(self, file_path: str, callback: Callable[[str], None]):
        self.file_path = Path(file_path).resolve()
        self.callback = callback
    
    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
            
        # Check if the modified file is our target file
        if Path(event.src_path).resolve() == self.file_path:
            self.callback(event.src_path)


class FileWatcher:
    """Watches a notebook file for changes and triggers callbacks."""
    
    def __init__(self, file_path: str, callback: Callable[[str], None]):
        self.file_path = Path(file_path).resolve()
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.event_handler = NotebookFileHandler(file_path, callback)
        
    def start(self) -> None:
        """Start watching the file."""
        if self.observer is not None:
            return  # Already started
            
        self.observer = Observer()
        # Watch the directory containing the file
        watch_dir = self.file_path.parent
        self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
        self.observer.start()
        
    def stop(self) -> None:
        """Stop watching the file."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
    
    def is_watching(self) -> bool:
        """Check if the watcher is currently active."""
        return self.observer is not None and self.observer.is_alive()


def watch_file(file_path: str, callback: Callable[[str], None]) -> FileWatcher:
    """Convenience function to create and start a file watcher."""
    watcher = FileWatcher(file_path, callback)
    watcher.start()
    return watcher
