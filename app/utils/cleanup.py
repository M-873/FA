import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Generator
from app.utils.logging import logger


class TempFileManager:
    """Manages temporary files and directories with context manager cleanup."""

    def __init__(self, prefix: str = "ai_content_"):
        self.prefix = prefix
        self.temp_dir: str = ""

    def __enter__(self) -> "TempFileManager":
        self.temp_dir = tempfile.mkdtemp(prefix=self.prefix)
        logger.info(f"Created temporary directory: {self.temp_dir}")
        return self

    def get_path(self, filename: str) -> str:
        """Returns an absolute path inside the temporary directory."""
        return os.path.join(self.temp_dir, filename)

    def cleanup(self) -> None:
        """Deletes the temporary directory and all contents."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Successfully cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Error cleaning up temporary directory {self.temp_dir}: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


@contextmanager
def temporary_working_dir(prefix: str = "ai_content_") -> Generator[TempFileManager, None, None]:
    """Context manager helper for safe temp file lifecycle."""
    mgr = TempFileManager(prefix=prefix)
    try:
        yield mgr
    finally:
        mgr.cleanup()
