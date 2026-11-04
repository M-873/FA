import logging
import re
import sys
from typing import Optional


class SecretRedactingFormatter(logging.Formatter):
    """Logging formatter that redacts known secrets, API tokens, and access tokens."""

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        self.patterns = [
            re.compile(r"(AIzaSy[A-Za-z0-9_-]{33})"),  # Gemini / Google API Key
            re.compile(r"(hf_[A-Za-z0-9]{34,})"),      # Hugging Face token
            re.compile(r"(sk-[A-Za-z0-9]{32,})"),      # OpenAI API Key
            re.compile(r"(EAAG[A-Za-z0-9]{50,})"),     # Meta Access Token
            re.compile(r"(access_token=)[^&\s]+", re.IGNORECASE),
            re.compile(r"(api_key=)[^&\s]+", re.IGNORECASE),
        ]

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        for pattern in self.patterns:
            formatted = pattern.sub(r"\1[REDACTED]", formatted)
        return formatted


def setup_logger(name: str = "ai_content_system", level_str: str = "INFO") -> logging.Logger:
    """Configures and returns a logger instance with secret redacting and UTF-8 stream safety."""
    logger = logging.getLogger(name)
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        # Stream handler with UTF-8 / errors='replace' support
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = SecretRedactingFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
