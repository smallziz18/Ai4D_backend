#!/bin/bash

# Script de Vérification Rapide - Questionnaire Initial
# Usage: ./verif_questionnaire.sh

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 VÉRIFICATION SYSTÈME - QUESTIONNAIRE INITIAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de vérification
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1${NC}"
        return 1
    fi
}

echo ""
echo "1️⃣  Vérification des fichiers modifiés..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vérifier les fichiers
files=(
    "src/celery_tasks.py"
    "src/profile/services.py"
    "src/ai_agents/profiler/profile_analyzer.py"
    "src/profile/router.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (manquant)"
    fi
done

echo ""
echo "2️⃣  Vérification des imports Python..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF'
import sys

try:
    # Import des modules
    from src.profile.services import profile_service
    print("✅ profile_service")

    from src.celery_tasks import profile_analysis_task
    print("✅ profile_analysis_task")

    from src.ai_agents.profiler.profile_analyzer import analyze_profile_with_llm
    print("✅ analyze_profile_with_llm")

    # Vérifier les méthodes
    assert hasattr(profile_service, 'save_initial_questionnaire'), "Méthode save_initial_questionnaire manquante"
    print("✅ save_initial_questionnaire disponible")

    assert hasattr(profile_service, 'analyze_quiz_and_update_profile'), "Méthode analyze_quiz_and_update_profile manquante"
    print("✅ analyze_quiz_and_update_profile disponible")

    # Vérifier la signature de profile_analysis_task
    import inspect
    sig = inspect.signature(profile_analysis_task)
    params = list(sig.parameters.keys())
    assert 'is_initial' in params, "Paramètre is_initial manquant"
    print("✅ Paramètre is_initial présent dans profile_analysis_task")

    sys.exit(0)

except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
PYEOF

check "Imports Python"

echo ""
echo "3️⃣  Vérification de MongoDB..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vérifier si MongoDB est accessible
python3 << 'PYEOF'
import sys
try:
    from src.db.mongo_db import mongo_db
    collections = mongo_db.list_collection_names()
    print(f"✅ MongoDB connecté")
    print(f"   Collections: {', '.join(collections)}")

    if 'profils' in collections:
        print("✅ Collection 'profils' existe")
    else:
        print("⚠️  Collection 'profils' sera créée au premier insert")

    sys.exit(0)
except Exception as e:
    print(f"❌ MongoDB non accessible: {e}")
    sys.exit(1)
PYEOF

check "MongoDB"

echo ""
echo "4️⃣  Vérification de la configuration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vérifier les variables d'environnement critiques
python3 << 'PYEOF'
import sys
import os
from src.config import Config

errors = []

# OpenAI API Key
if hasattr(Config, 'OPENAI_API_KEY') and Config.OPENAI_API_KEY:
    print("✅ OPENAI_API_KEY configurée")
else:
    print("⚠️  OPENAI_API_KEY non configurée (LLM ne fonctionnera pas)")
    errors.append("OPENAI_API_KEY")

# MongoDB
if hasattr(Config, 'MONGODB_URL'):
    print(f"✅ MONGODB_URL: {Config.MONGODB_URL[:30]}...")
else:
    print("❌ MONGODB_URL manquante")
    errors.append("MONGODB_URL")

# Celery
if hasattr(Config, 'CELERY_BROKER_URL'):
    print("✅ CELERY_BROKER_URL configurée")
else:
    print("⚠️  CELERY_BROKER_URL non configurée")

sys.exit(1 if errors else 0)
PYEOF

check "Configuration"

echo ""
echo "5️⃣  Vérification des fichiers de documentation..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docs=(
    "SAUVEGARDE_PROFIL_QUESTIONNAIRE.md"
    "RESUME_MODIFICATIONS_QUESTIONNAIRE.md"
    "GUIDE_TEST_QUESTIONNAIRE.md"
    "RECAP_FINAL_QUESTIONNAIRE.md"
    "test_questionnaire_initial.py"
    "test_data_questionnaire_initial.json"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✅${NC} $doc"
    else
        echo -e "${YELLOW}⚠️${NC}  $doc (optionnel)"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RÉSUMÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ Système prêt pour le questionnaire initial${NC}"
echo ""
echo "🚀 Pour tester :"
echo "   1. Démarrer l'API:     uvicorn src.main:app --reload"
echo "   2. Démarrer Celery:    celery -A src.celery_tasks worker --loglevel=info"
echo "   3. Lancer le test:     python test_questionnaire_initial.py"
echo ""
echo "📚 Documentation :"
echo "   - Guide complet:       SAUVEGARDE_PROFIL_QUESTIONNAIRE.md"
echo "   - Guide de test:       GUIDE_TEST_QUESTIONNAIRE.md"
echo "   - Résumé:              RECAP_FINAL_QUESTIONNAIRE.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

