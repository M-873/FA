import functools
import logging
from typing import Callable, Any, Type, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from app.utils.logging import logger


def with_retry(
    max_retries: int = 3,
    min_seconds: float = 2.0,
    max_seconds: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for retrying API calls with exponential backoff.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=min_seconds, max=max_seconds),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=before_sleep_log(logger, log_level=logging.INFO),
            reraise=True,
        )
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator

