import random
import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry_with_backoff(
    fn: Callable[[], Any],
    attempts: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
) -> Any:
    """Retries a synchronous callable with exponential backoff and jitter.

    Retries on connection errors, timeouts, 5xx server errors, and 429 rate limits.
    Re-raises immediately on authentication (401, 403) or validation (400) errors.
    """
    last_exception = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exception = exc
            status_code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)

            # Re-raise authentication or client validation errors immediately
            if status_code in (400, 401, 403):
                logger.error("Non-retryable error (HTTP %s): %s", status_code, exc)
                raise exc

            if attempt == attempts:
                logger.error("Operation failed after %d attempts: %s", attempts, exc)
                raise exc

            # Calculate exponential backoff delay with full jitter
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jittered_delay = random.uniform(0, delay)
            logger.warning(
                "Attempt %d/%d failed with error (%s). Retrying in %.2fs...",
                attempt,
                attempts,
                exc,
                jittered_delay,
            )
            time.sleep(jittered_delay)

    if last_exception:
        raise last_exception
