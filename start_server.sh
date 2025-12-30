#!/bin/bash
# Script pour lancer le serveur Uvicorn avec la bonne configuration

# Désactiver les signaux de rich-toolkit en utilisant une approche alternative
export PYTHONUNBUFFERED=1

# Vérifier si on veut le mode développement avec hot reload
DEV_MODE="${1:-prod}"

if [ "$DEV_MODE" = "dev" ]; then
  echo "🔄 Mode développement avec hot reload activé"
  uvicorn src:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dirs src \
    --log-level info
else
  echo "⚡ Mode production sans hot reload"
  uvicorn src:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
fi

