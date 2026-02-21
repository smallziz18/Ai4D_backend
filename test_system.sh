#!/bin/bash

# Script de Tests - Backend AI4D
# Testé sur: macOS avec zsh
# Usage: bash test_system.sh

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Démarrage des tests du système AI4D${NC}"
echo ""

# 1. Vérifier que les services sont prêts
echo -e "${YELLOW}📋 Test 1: Vérification des services${NC}"
echo "  ✓ PostgreSQL: vérifier avec: psql -U ai4d_user -d ai4d_db -c 'SELECT 1;'"
echo "  ✓ Redis: vérifier avec: redis-cli PING"
echo "  ✓ API: vérifier avec: curl http://localhost:8000/docs"
echo ""

# 2. Test CORS (OPTIONS)
echo -e "${YELLOW}📋 Test 2: CORS - Requête OPTIONS${NC}"
echo "Commande:"
echo 'curl -X OPTIONS http://localhost:8000/api/auth/v1/signup \\'
echo '  -H "Origin: http://localhost:3000" \\'
echo '  -H "Access-Control-Request-Method: POST" \\'
echo '  -v'
echo ""

# 3. Test inscription avec domaine CHIMIE
echo -e "${YELLOW}📋 Test 3: Inscription avec domaine CHIMIE${NC}"
echo "Commande:"
echo 'curl -X POST http://localhost:8000/api/auth/v1/signup \\'
echo '  -H "Content-Type: application/json" \\'
echo '  -d '\''{
  "nom": "Dupont",
  "prenom": "Jean",
  "username": "dupont_chimie",
  "email": "jean.dupont@example.com",
  "motDePasseHash": "SecurePass123!",
  "status": "Etudiant",
  "domaine": "CHIMIE"
}'\'
echo ""

# 4. Test inscription avec domaine DROIT
echo -e "${YELLOW}📋 Test 4: Inscription avec domaine DROIT (majuscules)${NC}"
echo "Commande:"
echo 'curl -X POST http://localhost:8000/api/auth/v1/signup \\'
echo '  -H "Content-Type: application/json" \\'
echo '  -d '\''{
  "nom": "Martin",
  "prenom": "Sophie",
  "username": "martin_droit",
  "email": "sophie.martin@example.com",
  "motDePasseHash": "SecurePass123!",
  "status": "Professeur",
  "domaine": "DROIT"
}'\'
echo ""

# 5. Test inscription avec domaine MARKETING
echo -e "${YELLOW}📋 Test 5: Inscription avec domaine Marketing (mixte)${NC}"
echo "Commande:"
echo 'curl -X POST http://localhost:8000/api/auth/v1/signup \\'
echo '  -H "Content-Type: application/json" \\'
echo '  -d '\''{
  "nom": "Laurent",
  "prenom": "Marie",
  "username": "laurent_marketing",
  "email": "marie.laurent@example.com",
  "motDePasseHash": "SecurePass123!",
  "status": "Etudiant",
  "domaine": "Marketing"
}'\'
echo ""

# 6. Vérification de la BDD
echo -e "${YELLOW}📋 Test 6: Vérification de la base de données${NC}"
echo "Vérifier que les profils Etudiant/Professeur ont le domaine correct:"
echo "  psql -U ai4d_user -d ai4d_db -c 'SELECT id, domaine FROM etudiant LIMIT 5;'"
echo "  psql -U ai4d_user -d ai4d_db -c 'SELECT id, domaine FROM professeur LIMIT 5;'"
echo ""

# 7. Tests Alembic
echo -e "${YELLOW}📋 Test 7: Vérification Alembic${NC}"
echo "Afficher la version actuelle:"
echo "  export DATABASE_URL='postgresql://ai4d_user:ai4d_password@localhost:5432/ai4d_db'"
echo "  alembic current"
echo ""

echo -e "${GREEN}✅ Script de tests préparé${NC}"
echo ""
echo -e "${BLUE}📝 Prochaines étapes:${NC}"
echo "1. Lancer l'API: python run.py"
echo "2. Lancer Celery: celery -A src.celery_tasks worker --loglevel=info"
echo "3. Exécuter les commandes curl ci-dessus"
echo "4. Vérifier les logs pour les erreurs"
echo ""
