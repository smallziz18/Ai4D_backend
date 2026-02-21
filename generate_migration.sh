#!/bin/bash
# Script simple pour générer une nouvelle migration Alembic
# Usage: ./generate_migration.sh "nom de la migration"

set -e

# Nom de la migration (par défaut: auto-generated)
MIGRATION_NAME="${1:-auto-generated changes}"

echo "🔨 Génération d'une nouvelle migration: $MIGRATION_NAME"

# Générer la migration
alembic revision --autogenerate -m "$MIGRATION_NAME"

echo "✅ Migration générée avec succès!"
echo ""
echo "📝 Prochaine étape:"
echo "   alembic upgrade head"

