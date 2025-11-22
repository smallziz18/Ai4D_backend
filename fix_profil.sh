#!/bin/bash

# Script de correction complète pour le problème de profil non sauvegardé

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 CORRECTION COMPLÈTE - PROFIL NON SAUVEGARDÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${YELLOW}⚠️  PROBLÈME IDENTIFIÉ :${NC}"
echo "   1. Le worker Celery utilise l'ancienne version du code"
echo "   2. La tâche profile_analysis_task échoue avec TypeError"
echo "   3. Aucun profil n'est sauvegardé dans MongoDB"
echo "   4. L'endpoint /recommendations retourne 404"
echo ""

# Étape 1 : Arrêter Celery
echo -e "${BLUE}📌 Étape 1/4 : Arrêt des workers Celery...${NC}"
pkill -9 -f "celery worker" 2>/dev/null
sleep 2

if pgrep -f "celery worker" > /dev/null; then
    echo -e "${RED}❌ Des workers Celery sont encore actifs${NC}"
    echo "   Processus trouvés :"
    pgrep -fa "celery worker"
    echo ""
    echo "   Tuez-les manuellement avec :"
    echo "   kill -9 \$(pgrep -f 'celery worker')"
    exit 1
else
    echo -e "${GREEN}✅ Tous les workers Celery sont arrêtés${NC}"
fi

# Étape 2 : Vérifier MongoDB
echo ""
echo -e "${BLUE}📌 Étape 2/4 : Vérification de MongoDB...${NC}"
python3 << 'PYEOF'
from src.db.mongo_db import mongo_db
try:
    count = mongo_db.profils.count_documents({})
    print(f"✅ MongoDB connecté - {count} profil(s) trouvé(s)")
except Exception as e:
    print(f"❌ Erreur MongoDB: {e}")
    exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ MongoDB non accessible${NC}"
    exit 1
fi

# Étape 3 : Créer le profil de test
echo ""
echo -e "${BLUE}📌 Étape 3/4 : Création du profil de test...${NC}"
python3 create_test_profile.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erreur lors de la création du profil${NC}"
    echo "   Vérifiez les logs ci-dessus"
else
    echo -e "${GREEN}✅ Profil créé ou déjà existant${NC}"
fi

# Étape 4 : Redémarrer Celery en arrière-plan
echo ""
echo -e "${BLUE}📌 Étape 4/4 : Redémarrage de Celery...${NC}"
echo -e "${YELLOW}   Cette étape va démarrer Celery en arrière-plan${NC}"
echo -e "${YELLOW}   Pour voir les logs : tail -f celery.log${NC}"
echo ""

read -p "Voulez-vous démarrer Celery maintenant ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[OoYy]$ ]]; then
    echo "Démarrage de Celery..."
    nohup celery -A src.celery_tasks worker --loglevel=info > celery.log 2>&1 &
    CELERY_PID=$!

    sleep 3

    if ps -p $CELERY_PID > /dev/null; then
        echo -e "${GREEN}✅ Celery démarré avec succès (PID: $CELERY_PID)${NC}"
        echo "   Logs: tail -f celery.log"
        echo "   Arrêter: kill $CELERY_PID"
        echo $CELERY_PID > celery.pid
    else
        echo -e "${RED}❌ Erreur au démarrage de Celery${NC}"
        echo "   Vérifiez celery.log"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Celery non démarré${NC}"
    echo "   Pour le démarrer manuellement :"
    echo "   celery -A src.celery_tasks worker --loglevel=info"
fi

# Résumé
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ CORRECTION TERMINÉE${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Prochaines étapes :"
echo "   1. Vérifier que Celery fonctionne : tail -f celery.log"
echo "   2. Vérifier le profil : python3 check_mongodb_profils.py"
echo "   3. Tester l'API :"
echo "      - GET /api/profile/v1/me"
echo "      - GET /api/profile/v1/recommendations"
echo "   4. Refaire le questionnaire pour générer les vraies recommandations"
echo ""
echo "📚 Documentation :"
echo "   - SOLUTION_URGENTE_CELERY.md"
echo "   - RECAP_FINAL_QUESTIONNAIRE.md"
echo ""

