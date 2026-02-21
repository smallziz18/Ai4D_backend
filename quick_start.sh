#!/bin/bash
# 🚀 Script de démarrage rapide pour AI4D Backend
# Lance tous les services nécessaires et vérifie leur fonctionnement

set -e  # Arrêter en cas d'erreur

echo "======================================================================"
echo "🚀 AI4D Backend - Démarrage Rapide"
echo "======================================================================"

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 1. Vérifier que Python est installé
echo ""
print_info "Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python trouvé: $PYTHON_VERSION"
else
    print_error "Python 3 n'est pas installé"
    exit 1
fi

# 2. Vérifier Redis
echo ""
print_info "Vérification de Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        print_success "Redis est démarré et répond"
    else
        print_info "Démarrage de Redis..."
        redis-server --daemonize yes
        sleep 2
        if redis-cli ping &> /dev/null; then
            print_success "Redis démarré avec succès"
        else
            print_error "Impossible de démarrer Redis"
            exit 1
        fi
    fi
else
    print_error "Redis n'est pas installé. Installez-le avec: brew install redis"
    exit 1
fi

# 3. Vérifier MongoDB
echo ""
print_info "Vérification de MongoDB..."
if command -v mongod &> /dev/null; then
    # Vérifier si MongoDB est déjà en cours d'exécution
    if pgrep -x "mongod" > /dev/null; then
        print_success "MongoDB est déjà démarré"
    else
        print_info "Démarrage de MongoDB..."
        # Créer le dossier data si nécessaire
        mkdir -p ~/data/db
        mongod --dbpath ~/data/db --fork --logpath ~/data/mongodb.log
        sleep 3
        if pgrep -x "mongod" > /dev/null; then
            print_success "MongoDB démarré avec succès"
        else
            print_error "Impossible de démarrer MongoDB"
            exit 1
        fi
    fi
else
    print_error "MongoDB n'est pas installé. Installez-le avec: brew install mongodb-community"
    exit 1
fi

# 4. Installer les dépendances Python si nécessaire
echo ""
print_info "Vérification des dépendances Python..."
if [ ! -d "venv" ] && [ ! -d ".venv" ] && [ -z "$VIRTUAL_ENV" ]; then
    print_info "Aucun environnement virtuel détecté. Installation des dépendances..."
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt --quiet
        print_success "Dépendances installées"
    else
        print_error "Fichier requirements.txt introuvable"
        exit 1
    fi
else
    print_success "Environnement virtuel détecté"
fi

# 5. Vérifier que Celery peut démarrer
echo ""
print_info "Vérification de Celery..."
if python3 -c "import celery" 2>/dev/null; then
    print_success "Celery est installé"
else
    print_error "Celery n'est pas installé"
    exit 1
fi

# 6. Exécuter les tests de validation
echo ""
print_info "Exécution des tests de validation..."
if python3 test_corrections.py > /dev/null 2>&1; then
    print_success "Tous les tests passent (6/6)"
else
    print_error "Certains tests ont échoué. Exécutez 'python test_corrections.py' pour plus de détails"
fi

# 7. Afficher les commandes pour démarrer les services
echo ""
echo "======================================================================"
echo "✨ Tous les prérequis sont installés !"
echo "======================================================================"
echo ""
echo "Pour démarrer le système, ouvrez 3 terminaux et exécutez :"
echo ""
echo "📍 Terminal 1 - Celery Worker :"
echo "   celery -A src.celery_tasks worker --loglevel=info"
echo ""
echo "📍 Terminal 2 - API FastAPI :"
echo "   python run.py"
echo ""
echo "📍 Terminal 3 - Tests Postman (optionnel) :"
echo "   Importer postman_roadmap_testing.json dans Postman"
echo ""
echo "======================================================================"
echo "📚 Documentation :"
echo "   - RESUME_FINAL.md : Guide complet"
echo "   - CORRECTIONS_README.md : Détails techniques"
echo "======================================================================"
echo ""

# 8. Demander si l'utilisateur veut démarrer automatiquement
read -p "Voulez-vous démarrer Celery et l'API maintenant ? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Démarrage de Celery en arrière-plan..."
    celery -A src.celery_tasks worker --loglevel=info > celery.log 2>&1 &
    CELERY_PID=$!
    sleep 3

    if kill -0 $CELERY_PID 2>/dev/null; then
        print_success "Celery démarré (PID: $CELERY_PID)"
        echo "   Logs: tail -f celery.log"
    else
        print_error "Erreur au démarrage de Celery"
        exit 1
    fi

    echo ""
    print_info "Démarrage de l'API FastAPI..."
    print_info "API accessible sur: http://localhost:8000"
    print_info "Documentation Swagger: http://localhost:8000/docs"
    print_info ""
    print_info "Appuyez sur Ctrl+C pour arrêter"

    # Démarrer l'API (bloquant)
    python run.py
else
    print_info "Utilisez les commandes ci-dessus pour démarrer manuellement"
fi

