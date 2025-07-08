import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MyEvenHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        print(event)


event_handler = MyEventHandler()
observer = Observer()
observer.schedule(event_handler, ".", recursive=True)
observer.start()


try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
