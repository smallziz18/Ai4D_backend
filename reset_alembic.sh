#!/bin/bash
# Guide complet pour réinitialiser et configurer Alembic
# Exécuter depuis la racine du projet backend_ai4_d

set -e  # Arrêter en cas d'erreur

echo "🚀 Démarrage de la réinitialisation d'Alembic..."

# 1. Charger les variables d'environnement
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Variables d'environnement chargées depuis .env"
else
    echo "⚠️  Attention: fichier .env non trouvé"
fi

# 2. Supprimer les anciennes migrations
echo "🗑️  Suppression des anciennes migrations..."
rm -f alembic/versions/*.py
rm -rf alembic/versions/__pycache__
echo "✅ Anciennes migrations supprimées"

# 3. Réinitialiser la base de données (ATTENTION: supprime toutes les données!)
echo "⚠️  ATTENTION: Cette opération va supprimer TOUTES les tables!"
read -p "Voulez-vous continuer? (oui/non): " response

if [ "$response" != "oui" ]; then
    echo "❌ Opération annulée"
    exit 0
fi

echo "🗄️  Réinitialisation de la base de données..."
python reset_db.py <<< "oui"

# 4. Créer une nouvelle migration initiale
echo "🔨 Création de la migration initiale..."
alembic revision --autogenerate -m "Initial migration with all tables"

# 5. Appliquer la migration
echo "⬆️  Application de la migration..."
alembic upgrade head

echo ""
echo "✅ =========================================="
echo "✅ Réinitialisation terminée avec succès!"
echo "✅ =========================================="
echo ""
echo "📊 Vérification des tables créées:"
psql $DATABASE_URL -c "\dt"
echo ""
echo "🎉 Vous pouvez maintenant créer vos utilisateurs!"

