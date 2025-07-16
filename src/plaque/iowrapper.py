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
        # Mirror to original stream for command line visibility
        if self._original:
            self._original.write(message)
            self._original.flush()  # Ensure immediate output

    def seek(self, offset, whence=io.SEEK_SET):
        self.buffer.seek(offset, whence)

    def flush(self):
        # Flush both buffer and original stream
        self.buffer.flush()
        if self._original and hasattr(self._original, "flush"):
            self._original.flush()
