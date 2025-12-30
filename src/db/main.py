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
)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
