import io
import sys


class NotebookStdout:
    def __init__(self, original_stdout=None):
        self._original = original_stdout or sys.stdout
        self.buffer = io.StringIO()

    def fileno(self):
        if hasattr(self._original, "fileno"):
            return self._original.fileno()
        raise io.UnsupportedOperation("fileno() not supported on this stream")

    def close(self):
        # self.buffer.close()
        pass

    def getvalue(self):
        return self.buffer.getvalue()

    def write(self, message):
        self.buffer.write(message)

    def seek(self, offset, whence=io.SEEK_SET):
        self.buffer.seek(offset, whence)
