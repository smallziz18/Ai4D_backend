# ✅ CHECKLIST FINALE - Déploiement Backend

## 🎯 Récapitulatif des Modifications

### Backend adapté pour : Profil créé APRÈS questionnaire initial

**Date** : 18 novembre 2025  
**Statut** : ✅ Prêt pour tests

---

## 📋 Checklist de Déploiement

### 1. ❓ Migrations SQL - À FAIRE ?

**Réponse : NON** ✅

Les modifications sont **purement logiques** (pas de changement de structure SQL).

- ✅ Tables `utilisateur`, `etudiant`, `professeur` inchangées
- ✅ Aucune colonne ajoutée/supprimée
- ✅ Seul le **moment de création** des profils SQL a changé

**Détails** : Voir `MIGRATIONS_INFO.md`

**Vérification optionnelle** :
```bash
# Si tu veux quand même vérifier que tout est à jour
alembic current
alembic upgrade head  # Si des migrations en attente
```

---

### 2. 🔄 Services à Redémarrer

#### A. Worker Celery (OBLIGATOIRE)

**Pourquoi** : Nouvelle signature de `profile_analysis_task` avec paramètre `is_initial`

```bash
# 1. Arrêter le worker actuel
pkill -9 -f "celery worker"

# 2. Démarrer le nouveau worker
cd /Users/smallziz/Documents/project\ ai4d/backend_ai4_d
celery -A src.celery_tasks worker --loglevel=info

# Vérifier dans les logs :
# [tasks]
#   . profile_analysis_task
#   . generate_profile_question_task
```

#### B. API FastAPI (RECOMMANDÉ)

```bash
# Si déjà lancé, Ctrl+C puis :
uvicorn src.main:app --reload --port 8000

# Ou avec Docker :
docker-compose restart backend
```

---

### 3. 🧪 Tests de Validation

#### Test 1 : Signup sans profil

```bash
# 1. Créer un nouveau compte
curl -X POST http://localhost:8000/api/auth/v1/signup \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Test",
    "prenom": "User",
    "username": "testuser123",
    "email": "test123@example.com",
    "motDePasseHash": "password123",
    "status": "Etudiant"
  }'

# 2. Vérifier : aucun profil MongoDB
curl http://localhost:8000/api/profile/v1/has-profile \
  -H "Authorization: Bearer TOKEN"

# Attendu :
# {
#   "has_profile": false,
#   "questionnaire_initial_complete": false
# }
```

#### Test 2 : Questionnaire initial crée le profil

```bash
# 1. Soumettre le questionnaire
curl -X POST http://localhost:8000/api/profile/v1/analyze_quiz \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_data_questionnaire_initial.json

# Récupérer task_id de la réponse

# 2. Attendre l'analyse (quelques secondes)
sleep 5

# 3. Vérifier le résultat
curl http://localhost:8000/api/profile/v1/analysis_result/TASK_ID \
  -H "Authorization: Bearer TOKEN"

# Attendu : {"status": "success", "result": {...}}

# 4. Vérifier que le profil existe maintenant
curl http://localhost:8000/api/profile/v1/has-profile \
  -H "Authorization: Bearer TOKEN"

# Attendu :
# {
#   "has_profile": true,
#   "questionnaire_initial_complete": true
# }

# 5. Vérifier les recommandations
curl http://localhost:8000/api/profile/v1/recommendations \
  -H "Authorization: Bearer TOKEN"

# Attendu : 200 avec liste de recommandations
```

#### Test 3 : Profil SQL créé

```bash
# Vérifier dans PostgreSQL
psql -U postgres -d ai4d

# Requête SQL :
SELECT u.id, u.username, u.status, 
       e.id as etudiant_id, p.id as professeur_id
FROM utilisateur u
LEFT JOIN etudiant e ON e.id = u.id
LEFT JOIN professeur p ON p.id = u.id
WHERE u.username = 'testuser123';

# Attendu :
# - Ligne dans utilisateur
# - Ligne dans etudiant OU professeur (selon status)
```

#### Test 4 : Profil MongoDB créé

```bash
# Vérifier dans MongoDB
mongosh ai4d

db.profils.findOne({"utilisateur_id": "UUID_DU_TEST_USER"})

# Attendu :
# - questionnaire_initial_complete: true
# - questionnaire_reponses: [...]
# - analyse_questions_ouvertes: {...}
# - recommandations: [...]
```

---

### 4. 🔍 Vérifications Système

#### Base de données

```bash
# PostgreSQL
./check_database.sh

# MongoDB
python3 check_mongodb_profils.py
```

#### Logs Celery

```bash
# Vérifier qu'il n'y a pas d'erreur TypeError
tail -f celery.log | grep -i "error\|profile_analysis"
```

#### Logs API

```bash
# Vérifier les requêtes
tail -f api.log | grep -E "signup|analyze_quiz|has-profile"
```

---

### 5. 📊 Endpoints Clés

| Endpoint | Avant | Après |
|----------|-------|-------|
| `POST /signup` | Crée user + profil SQL | Crée user uniquement ✅ |
| `GET /me` | 200 (auto-créé si absent) | 404 si absent ✅ |
| `GET /has-profile` | N'existait pas | Nouveau endpoint ✅ |
| `POST /analyze_quiz` | Gamification seulement | Détecte initial + crée profils ✅ |
| `GET /recommendations` | 404 si pas de profil | 404 si pas de profil ✅ |

---

### 6. 🚀 Flux Complet Validé

```
1. User signup
   ↓
   [Utilisateur créé dans PostgreSQL]
   [Aucun profil Mongo/SQL]
   
2. GET /has-profile → false
   ↓
   [Frontend redirige vers /questionnaire]
   
3. User répond au questionnaire
   ↓
   POST /analyze_quiz
   ↓
   [Celery détecte is_initial=True]
   
4. Tâche Celery :
   ├─ Crée profil MongoDB
   ├─ Sauvegarde questionnaire + analyse LLM
   ├─ Crée profil SQL (Etudiant/Professeur)
   └─ Génère recommandations
   
5. GET /has-profile → true
   ↓
   [Frontend redirige vers /dashboard]
   
6. GET /me → 200 ✅
   GET /recommendations → 200 ✅
```

---

### 7. 🐛 Troubleshooting

#### Erreur : TypeError dans Celery

**Symptôme** : `profile_analysis_task() takes 2 positional arguments but 3 were given`

**Solution** : Redémarrer le worker Celery (voir section 2.A)

#### Erreur : Profil pas créé après questionnaire

**Vérifications** :
1. Celery tourne ? `ps aux | grep celery`
2. Logs Celery : `tail -f celery.log`
3. Task réussie ? `GET /analysis_result/{task_id}`

#### Erreur : /recommendations → 404

**Cause** : Profil MongoDB pas encore créé ou recommandations vides

**Solution** :
```bash
# Vérifier MongoDB
python3 check_mongodb_profils.py

# Si vide, refaire le questionnaire
```

---

### 8. 📁 Documentation Créée

| Fichier | Usage |
|---------|-------|
| `MIGRATIONS_INFO.md` | Explique pourquoi pas de migration |
| `RECAP_FINAL_QUESTIONNAIRE.md` | Vue d'ensemble complète |
| `CORRECTION_IMMEDIATE.md` | Fix Celery + profil |
| `FIX_RAPIDE.md` | Quick fix 30s |
| `check_database.sh` | Vérif PostgreSQL |
| `check_mongodb_profils.py` | Vérif MongoDB |
| `test_questionnaire_initial.py` | Script de test |
| `CHECKLIST_FINALE.md` | Ce fichier |

---

### 9. ✅ Go/No-Go Déploiement

Avant de déployer en production, vérifier :

- [ ] Worker Celery redémarré avec nouveau code
- [ ] API FastAPI redémarrée
- [ ] Test signup → has-profile = false ✅
- [ ] Test questionnaire → profil créé (Mongo + SQL) ✅
- [ ] Test /me et /recommendations → 200 ✅
- [ ] Logs Celery propres (pas d'erreur TypeError)
- [ ] MongoDB contient profils avec recommandations
- [ ] PostgreSQL contient entrées Etudiant/Professeur

**Si tous ✅ → Prêt pour production ! 🚀**

---

## 🎉 Résumé Final

### Changements Backend Appliqués :

1. ✅ Signup crée uniquement le compte (pas de profil)
2. ✅ /me retourne 404 si pas de profil (pas d'auto-création)
3. ✅ Nouveau endpoint /has-profile pour le frontend
4. ✅ Questionnaire initial crée profil MongoDB + SQL
5. ✅ Tâche Celery adaptée avec paramètre is_initial
6. ✅ Méthode ensure_sql_profile_after_questionnaire ajoutée
7. ✅ Analyse LLM des questions ouvertes sauvegardée
8. ✅ Recommandations personnalisées générées

### Migrations SQL :

❌ **Aucune migration nécessaire** (structure SQL inchangée)

### Prochaine Étape :

**Redémarrer Celery + Tester le flux complet**

---

**Date** : 18 novembre 2025  
**Version** : 2.0 - Profil après questionnaire  
**Statut** : ✅ Prêt pour tests

