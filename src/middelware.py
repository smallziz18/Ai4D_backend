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
    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
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
            f"→ {response.status_code} | {duration}s | from {client_host} on port {client_port}"
        )

        return response

    # Ajout des origines autorisées pour le frontend Nuxt
    origins = [
        "http://localhost:3000",  # Nuxt dev server
        "http://127.0.0.1:3000",
    ]

    trusted_hosts = [
        "localhost",
        "127.0.0.1",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # Origines autorisées
        allow_credentials=True,  # Autoriser cookies / headers d'auth
        allow_methods=["*"],  # Autoriser toutes les méthodes (GET, POST, etc.)
        allow_headers=["*"],  # Autoriser tous les headers
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts,
    )
