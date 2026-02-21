# Plan de Correction Complet - Backend AI4D

## Problèmes Identifiés

### 1. ❌ Erreur Event Loop dans Celery Tasks
**Erreur:** `IllegalStateChangeError: Method 'close()' can't be called here`
**Cause:** Mauvaise gestion des boucles asyncio dans les tâches Celery
**Solution:** Utiliser des boucles isolées pour chaque opération async

### 2. ❌ Enum Domaine - Erreur "CHIMIE" invalide  
**Erreur:** `invalid input value for enum domaine: "CHIMIE"`
**Cause:** L'enum attend "Chimie" mais reçoit "CHIMIE" (uppercase)
**Solution:** Normaliser la conversion dans le router

### 3. ❌ Alembic - Can't load plugin sqlalchemy.dialects:driver
**Erreur:** `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver`
**Cause:** alembic.ini a une URL vide, env.py doit lire DATABASE_URL
**Solution:** S'assurer que DATABASE_URL est dans l'environnement

### 4. ❌ Niveau toujours "Débutant" malgré bonnes réponses
**Cause:** Algorithme de détection trop sévère
**Solution:** Rendre l'algorithme plus intelligent et moins sévère

### 5. ❌ Roadmap non créé après questionnaire
**Cause:** Event loop closed + timeout
**Solution:** Augmenter le timeout et corriger la gestion des loops

### 6. ❌ CORS - OPTIONS non supporté
**Erreur:** `405 Method Not Allowed` sur OPTIONS
**Solution:** Ajouter des routes OPTIONS explicites

### 7. ❌ Questionnaire trop difficile et non adapté au domaine
**Cause:** Questions trop techniques pour non-informaticiens
**Solution:** Adapter les questions au domaine de l'utilisateur

### 8. ❌ Profils non isolés entre utilisateurs
**Cause:** Cache ou clé MongoDB mal gérée
**Solution:** Vérifier l'isolation par utilisateur_id

## Ordre d'Exécution des Corrections

1. ✅ **Créer une nouvelle migration Alembic propre**
2. ✅ **Corriger la gestion des event loops dans celery_tasks.py**
3. ✅ **Normaliser le domaine dans users/router.py**
4. ✅ **Améliorer l'algorithme de détection de niveau**
5. ✅ **Ajouter routes OPTIONS pour CORS**
6. ✅ **Adapter les questions au domaine utilisateur**
7. ✅ **Augmenter les timeouts Celery**
8. ✅ **Tester l'isolation des profils**

## Fichiers à Modifier

1. `/src/celery_tasks.py` - Event loops + timeouts
2. `/src/users/router.py` - Normalisation domaine + OPTIONS
3. `/src/users/models.py` - Vérifier enum Domaine
4. `/alembic/env.py` - Vérifier lecture DATABASE_URL
5. `/src/profile/services.py` - Isolation profils
6. `/src/ai_agents/profiler/profile_analyzer.py` - Questions adaptées

## Commandes de Test

```bash
# 1. Générer nouvelle migration
alembic revision --autogenerate -m "fix_domaine_enum_and_verification_token"

# 2. Appliquer la migration
alembic upgrade head

# 3. Vérifier l'état de la BDD
psql $DATABASE_URL -c "\d+ etudiant"
psql $DATABASE_URL -c "\d+ professeur"

# 4. Tester l'inscription avec domaine
curl -X POST http://localhost:8000/api/auth/v1/signup \
  -H 'Content-Type: application/json' \
  -d '{
    "nom": "Test",
    "prenom": "User",
    "username": "testuser",
    "email": "test@example.com",
    "motDePasseHash": "password123",
    "status": "Etudiant",
    "domaine": "Chimie"
  }'

# 5. Vérifier CORS
curl -X OPTIONS http://localhost:8000/api/auth/v1/signup -i

# 6. Tester Celery
celery -A src.celery_tasks worker --loglevel=info
```

## État Actuel

- [ ] Event loops corrigés
- [ ] Domaine normalisé
- [ ] Alembic fonctionnel
- [ ] Niveau détecté correctement
- [ ] Roadmap créé
- [ ] CORS fonctionnel
- [ ] Questions adaptées
- [ ] Profils isolés

## Priorité 1 - Corrections Urgentes

1. Corriger event loops (bloque tout)
2. Fixer enum Domaine (bloque inscription)
3. Ajouter OPTIONS CORS (bloque frontend)
