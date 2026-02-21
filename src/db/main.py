from typing import Any, AsyncGenerator, Union

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession
from src.config import Config

# Utiliser NullPool pour éviter les problèmes de session avec Celery
# NullPool crée une nouvelle connexion pour chaque interaction et la ferme immédiatement
engine = create_async_engine(
    Config.DATABASE_URL,
    poolclass=NullPool,  # Important pour Celery qui fork les processus
    pool_pre_ping=True,
    echo=False,
)

# Crée un sessionmaker asynchrone au module-level pour réutilisation
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[Union[AsyncSession, Any], Any]:
    """
    Générateur de session async avec gestion propre des erreurs.
    Utilisé comme dependency dans FastAPI.
    """
    session = async_session()
    try:
        yield session
        # Commit si pas d'erreur
        if session.in_transaction():
            await session.commit()
    except Exception as e:
        # Rollback en cas d'erreur
        if session.in_transaction():
            await session.rollback()
        raise
    finally:
        # Fermeture sécurisée de la session
        try:
            await session.close()
        except Exception:
            # Ignorer les erreurs de fermeture si la session est déjà fermée ou en état invalide
            pass
