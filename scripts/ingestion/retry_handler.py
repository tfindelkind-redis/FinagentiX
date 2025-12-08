"""Retry handler with exponential backoff"""
import time
import logging
from typing import Callable, List, Tuple, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 5, 
                       delays: List[int] = None,
                       exception_types: Tuple = (Exception,)):
    """
    Decorator for retry logic with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delays: List of delays (seconds) for each retry. Default: [2,4,8,16,32,60]
        exception_types: Tuple of exception types to catch and retry
    
    Returns:
        Decorated function that retries on failure
    """
    if delays is None:
        delays = [2, 4, 8, 16, 32, 60]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[any]:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        delay = delays[min(attempt, len(delays) - 1)]
                        logger.info(
                            f"Retry {attempt + 1}/{max_retries} after {delay}s "
                            f"(error: {str(e)[:50]})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Failed after {max_retries} attempts: {e}"
                        )
            
            return None
        
        return wrapper
    return decorator
