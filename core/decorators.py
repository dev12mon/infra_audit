# higher-order functions, retries, and execution timing

import time
import functools
import logging
from typing import Callable, Any
from .exceptions import APIConnectionError

logger = logging.getLogger(__name__)

def time_it(func: Callable) -> Callable:
    """Decorator to measure the execution time of functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Execution of {func.__name__} took {end_time - start_time:.4f} seconds.")
        return result
    return wrapper

def retry_with_backoff(max_attempts: int = 3, delay: int = 2, exceptions: tuple = (Exception,)) -> Callable:
    """
    Decorator that retries a function with exponential backoff if specific exceptions are raised.
    Critical for resilient API calls in CI/CD and automation scripts.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
                        raise APIConnectionError(f"Failed after {max_attempts} retries.") from e
                    
                    sleep_time = delay * (2 ** (attempt - 1)) # Exponential backoff
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
        return wrapper
    return decorator