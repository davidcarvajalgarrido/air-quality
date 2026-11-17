"""
Capa de seguridad: comprobar API key y, si es válida, aplicar rate limit.

FastAPI llama a `require_api_key` vía Depends(...) ANTES de entrar a la ruta.
"""

import logging

from fastapi import HTTPException, Query

import config
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)


def require_api_key(
    api_key: str | None = Query(
        default=None,
        description="Clave de acceso (misma que API_KEY en .env)",
    ),
) -> str:
    """
    1) Servidor sin API_KEY en .env → 503 (mal configurado).
    2) Cliente sin clave o clave distinta → 401.
    3) Clave OK → rate limit; si pasa, devolvemos la clave (el endpoint sigue).
    """
    if not config.API_KEY:
        logger.error("auth 503: API_KEY no configurada en el servidor")
        raise HTTPException(
            status_code=503,
            detail="API_KEY no configurada en el servidor",
        )

    if not api_key or api_key != config.API_KEY:
        logger.warning("auth 401: api_key ausente o inválida")
        raise HTTPException(
            status_code=401,
            detail="API key inválida o ausente",
        )

    check_rate_limit(api_key)
    return api_key
