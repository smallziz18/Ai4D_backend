from __future__ import with_statement
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Ajoute la racine du projet au PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

config = context.config
fileConfig(config.config_file_name)

# Import des modèles directement (éviter imports circulaires via src/__init__.py)
from src.users.models import Utilisateur, Etudiant, Professeur
target_metadata = Utilisateur.metadata

print("[INFO] target_metadata loaded successfully")

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Utiliser psycopg2 (synchrone) pour Alembic
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Utiliser psycopg2 (synchrone) pour Alembic
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
