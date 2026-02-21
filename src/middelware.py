import time
from fastapi import FastAPI
import logging
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import os

logger = logging.getLogger('uvicorn.access')
logger.disabled = True

# Configure un logger custom
logger = logging.getLogger("request_logger")
logger.setLevel(logging.INFO)

# Ajoute un handler console coloré
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Contrôle si on veut ré-émettre les exceptions pour voir la trace brute
PAUSE_ERROR_HANDLING = os.getenv("PAUSE_ERROR_HANDLING", "false").lower() in ("1", "true", "yes")


def register_middlewares(app: FastAPI):
    """
    Enregistre les middlewares dans le bon ordre.
    L'ordre CORRECT est: custom_logging → TrustedHost → CORS (exécution inverse)
    """

    # ============ MIDDLEWARE 1 (déclaré en 1er, exécuté en dernier - le plus "inner") ============
    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        # Ignorer les OPTIONS - laisser les autres middlewares les gérer
        if request.method == "OPTIONS":
            return await call_next(request)

        start_time = time.time()

        try:
            # Exécution de la requête
            response = await call_next(request)
        except Exception as exc:
            # Log de l'exception avec traceback
            logger.exception(f"Unhandled exception for {request.method} {request.url.path}: {exc}")

            # Si on veut voir les erreurs brutes dans la console (utile en dev),
            # on ré-émet l'exception pour que Uvicorn/FastAPI affiche la stack complète.
            if PAUSE_ERROR_HANDLING:
                raise

            # Sinon on renvoie une réponse 500 générique (comportement sécurisé pour prod)
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

        # Calcul du temps
        duration = round(time.time() - start_time, 3)

        # IP du client
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else "unknown"

        # Log final formaté
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} | {duration}s | from {client_host}:{client_port}"
        )

        return response

    # ============ MIDDLEWARE 2 (déclaré en 2e, exécuté en 2e) ============
    trusted_hosts = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    ]

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts,
    )

    # ============ MIDDLEWARE 3 (ajouté en dernier, exécuté EN PREMIER - le plus "outer") ============
    # ⚠️ IMPORTANT: CORS DOIT ÊTRE AJOUTÉ EN DERNIER POUR S'EXÉCUTER EN PREMIER
    origins = [
        "http://localhost:3000",     # Nuxt dev local
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
        "*",                          # Autoriser tous en dev
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )

