"""
Rate limit en memoria: máximo N peticiones por API key cada 60 segundos.
"""

import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException

import config

logger = logging.getLogger(__name__)

_hits: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(api_key: str) -> None:
    """Si esta clave supera RATE_LIMIT_PER_MINUTE en 60 s → 429."""
    now = time.monotonic()
    window = 60.0
    q = _hits[api_key]

    while q and (now - q[0]) > window:
        q.popleft()

    if len(q) >= config.RATE_LIMIT_PER_MINUTE:
        logger.warning(
            "rate limit 429: demasiadas peticiones (max=%s / 60s)",
            config.RATE_LIMIT_PER_MINUTE,
        )
        raise HTTPException(
            status_code=429,
            detail="Demasiadas peticiones; esperad un minuto",
        )

    q.append(now)
