"""
Script Python pour réinitialiser complètement la base de données
Usage: python reset_db.py
"""

import os
import sys
import asyncio
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config

settings = Config()


async def reset_database():
    """Supprime toutes les tables et réinitialise la base de données"""

    print("🔥 Réinitialisation de la base de données...")
    print(f"📍 Base de données: {settings.DATABASE_URL.split('@')[-1]}")

    # Créer le moteur
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # Supprimer toutes les tables et types ENUM
            print("🗑️  Suppression de toutes les tables, types ENUM et schémas...")

            # Supprimer tous les types ENUM personnalisés
            await conn.execute(text("DROP TYPE IF EXISTS statututilisateur CASCADE;"))
            await conn.execute(text("DROP TYPE IF EXISTS domaine CASCADE;"))

            # Supprimer le schéma public et le recréer
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
            await conn.execute(text("CREATE SCHEMA public;"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))

            print("✅ Base de données complètement nettoyée!")
            print("✅ Tous les types ENUM supprimés!")

    except Exception as e:
        print(f"❌ Erreur lors de la réinitialisation: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("⚠️  ATTENTION: SUPPRESSION TOTALE DE TOUTES LES DONNÉES!")
    print("=" * 60)
    print()
    print("Cette opération va:")
    print("  - Supprimer TOUTES les tables")
    print("  - Supprimer TOUS les types ENUM")
    print("  - Supprimer TOUTES les données")
    print()

    response = input("Êtes-vous sûr de vouloir continuer? (oui/non): ")

    if response.lower() in ["oui", "o", "yes", "y"]:
        asyncio.run(reset_database())
        print()
        print("=" * 60)
        print("📝 ÉTAPES SUIVANTES:")
        print("=" * 60)
        print("1. Supprimez les anciennes migrations:")
        print("   rm -f alembic/versions/*.py")
        print()
        print("2. Créez une nouvelle migration:")
        print("   alembic revision --autogenerate -m 'Initial migration'")
        print()
        print("3. Appliquez la migration:")
        print("   alembic upgrade head")
        print()
        print("Ou utilisez le script automatisé:")
        print("   chmod +x reset_alembic.sh && ./reset_alembic.sh")
        print("=" * 60)
    else:
        print("❌ Opération annulée.")

