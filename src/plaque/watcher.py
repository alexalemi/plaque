"""File watcher for live updates."""

import time
import threading
from typing import Callable, Optional
from pathlib import Path
import logging

from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


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

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        # Check if the destination file is our target file
        if (
            hasattr(event, "dest_path")
            and Path(event.dest_path).resolve() == self.file_path
        ):
            self.callback(event.dest_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        # Check if the created file is our target file
        if Path(event.src_path).resolve() == self.file_path:
            self.callback(event.src_path)


class FileWatcher:
    """Watches a notebook file for changes and triggers callbacks."""

    def __init__(self, file_path: str, callback: Callable[[str], None]):
        self.file_path = Path(file_path).resolve()
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.event_handler = NotebookFileHandler(file_path, callback)
        self.use_polling = False

    def start(self) -> None:
        """Start watching the file."""
        if self.observer is not None:
            return  # Already started

        # Try to use native file watching first
        try:
            self.observer = Observer()
            # Watch the directory containing the file
            watch_dir = self.file_path.parent
            self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
            self.observer.start()
            logger.debug(f"Started native file watching for {self.file_path}")
        except OSError as e:
            if "inotify" in str(e).lower() or "too many" in str(e).lower():
                # inotify limit reached, fall back to polling
                logger.warning(f"inotify limit reached, falling back to polling: {e}")
                self._start_polling()
            else:
                raise
        except Exception as e:
            # For any other errors, try falling back to polling
            logger.warning(f"Native file watching failed, falling back to polling: {e}")
            self._start_polling()

    def _start_polling(self) -> None:
        """Start polling-based file watching as fallback."""
        try:
            self.observer = PollingObserver()
            watch_dir = self.file_path.parent
            self.observer.schedule(self.event_handler, str(watch_dir), recursive=False)
            self.observer.start()
            self.use_polling = True
            logger.info(f"Started polling-based file watching for {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to start polling watcher: {e}")
            raise

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
