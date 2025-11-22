#!/bin/bash

# Script de vérification rapide de la base de données PostgreSQL

echo "🔍 VÉRIFICATION DE LA BASE DE DONNÉES"
echo "======================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Vérifier si PostgreSQL est accessible
echo "1. Test de connexion PostgreSQL..."

# Essayer de se connecter (adapter selon votre configuration)
psql -U postgres -d ai4d -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PostgreSQL accessible${NC}"

    echo ""
    echo "2. Tables existantes :"
    psql -U postgres -d ai4d -c "\dt" 2>/dev/null | grep -E "utilisateur|etudiant|professeur|verification"

    echo ""
    echo "3. Structure table utilisateur :"
    psql -U postgres -d ai4d -c "\d utilisateur" 2>/dev/null

    echo ""
    echo "4. Compte d'utilisateurs :"
    psql -U postgres -d ai4d -c "SELECT status, COUNT(*) FROM utilisateur GROUP BY status;" 2>/dev/null

    echo ""
    echo "5. Profils SQL créés :"
    ETUDIANTS=$(psql -U postgres -d ai4d -t -c "SELECT COUNT(*) FROM etudiant;" 2>/dev/null)
    PROFESSEURS=$(psql -U postgres -d ai4d -t -c "SELECT COUNT(*) FROM professeur;" 2>/dev/null)
    echo "   Étudiants : $ETUDIANTS"
    echo "   Professeurs : $PROFESSEURS"

else
    echo -e "${RED}❌ PostgreSQL non accessible${NC}"
    echo ""
    echo "Essayez :"
    echo "  - Vérifier que PostgreSQL tourne : pg_ctl status"
    echo "  - Ou via Docker : docker ps | grep postgres"
    echo "  - Adapter les identifiants dans ce script"
fi

echo ""
echo "======================================="
echo "📝 Note : Si des tables manquent, exécutez:"
echo "   alembic upgrade head"
echo ""

