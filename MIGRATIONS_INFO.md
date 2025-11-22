# ℹ️ Migrations SQL - Aucune Migration Nécessaire

## 🎯 Question : Dois-je exécuter des migrations ?

**Réponse : NON**, aucune migration SQL n'est nécessaire pour les changements effectués.

## 📋 Pourquoi ?

Les modifications apportées concernent **uniquement la logique métier**, pas la structure SQL des tables :

### Ce qui a changé (Logique uniquement) :

1. **Endpoint `/signup`** :
   - ❌ **Avant** : Créait automatiquement l'entrée dans `etudiant` ou `professeur`
   - ✅ **Après** : Crée uniquement l'entrée dans `utilisateur`

2. **Création des profils SQL** :
   - ✅ **Nouvelle méthode** : `ensure_sql_profile_after_questionnaire()`
   - ✅ **Moment** : Appelée après le questionnaire initial par la tâche Celery
   - ✅ **Résultat** : Crée l'entrée `etudiant` ou `professeur` avec les données du LLM

### Structure SQL inchangée :

```sql
-- Table utilisateur (INCHANGÉE)
CREATE TABLE utilisateur (
    id UUID PRIMARY KEY,
    nom VARCHAR,
    prenom VARCHAR,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    motDePasseHash VARCHAR,
    status ENUM('Etudiant', 'Professeur'),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE
);

-- Table etudiant (INCHANGÉE)
CREATE TABLE etudiant (
    id UUID PRIMARY KEY REFERENCES utilisateur(id),
    niveau_technique INTEGER,
    competences TEXT[],
    objectifs_apprentissage TEXT,
    motivation TEXT,
    niveau_energie INTEGER
);

-- Table professeur (INCHANGÉE)
CREATE TABLE professeur (
    id UUID PRIMARY KEY REFERENCES utilisateur(id),
    niveau_experience INTEGER,
    specialites TEXT[],
    motivation_principale TEXT,
    niveau_technologique INTEGER
);
```

**Aucune colonne ajoutée, supprimée ou modifiée** = **Aucune migration nécessaire**.

---

## ✅ Vérification rapide

Si tu veux quand même vérifier que ta base est à jour :

```bash
# 1. Vérifier l'état actuel
alembic current

# 2. Appliquer les migrations en attente (s'il y en a)
alembic upgrade head

# 3. Vérifier l'historique
alembic history
```

**Résultat attendu** : Les migrations existantes (init, verification tokens, etc.) sont déjà appliquées.

---

## 🔄 Flux complet avec les nouvelles modifications

### 1. Signup (Utilisateur uniquement)
```python
# src/users/services.py - create_user()
utilisateur = Utilisateur(
    nom=data.nom,
    prenom=data.prenom,
    username=data.username,
    email=normalized_email,
    motDePasseHash=generate_password_hash(data.motDePasseHash),
    status=data.status,  # "Etudiant" ou "Professeur"
    created_at=datetime.now(),
    updated_at=datetime.now()
)
session.add(utilisateur)
await session.commit()
# ⚠️ Pas de création dans etudiant/professeur ici
```

**État SQL après signup :**
- ✅ 1 ligne dans `utilisateur`
- ❌ 0 ligne dans `etudiant` ou `professeur`

### 2. Questionnaire initial soumis
```python
# src/celery_tasks.py - profile_analysis_task(is_initial=True)

# Étape 1 : Créer profil MongoDB
profile = await profile_service.create_profile(...)

# Étape 2 : Sauvegarder questionnaire + analyse LLM
await profile_service.save_initial_questionnaire(...)

# Étape 3 : Créer profil SQL (Etudiant/Professeur)
await UserService.ensure_sql_profile_after_questionnaire(
    user_uuid,
    status_enum,  # ETUDIANT ou PROFESSEUR
    details       # {niveau, competences, objectifs, motivation, energie}
)
```

**État SQL après questionnaire :**
- ✅ 1 ligne dans `utilisateur`
- ✅ 1 ligne dans `etudiant` OU `professeur` (selon le status)
- ✅ 1 document dans MongoDB `profils`

---

## 🗃️ Tables SQL actuelles

Vérifier que les tables existent bien :

```bash
# Se connecter à PostgreSQL
psql -U votre_user -d votre_db

# Lister les tables
\dt

# Vérifier la structure
\d utilisateur
\d etudiant
\d professeur
```

**Tables attendues :**
- `utilisateur`
- `etudiant`
- `professeur`
- `verification_token`
- `alembic_version`

---

## 🔍 En cas de doute

Si tu constates des problèmes (tables manquantes, colonnes incorrectes), tu peux :

### Option 1 : Réinitialiser complètement (⚠️ PERTE DE DONNÉES)

```bash
# Supprimer toutes les tables
alembic downgrade base

# Recréer toutes les tables
alembic upgrade head
```

### Option 2 : Vérifier l'état et appliquer manuellement

```bash
# Générer une migration si vraiment nécessaire
alembic revision --autogenerate -m "description"

# Vérifier le contenu généré
cat migrations/versions/[fichier_généré].py

# Appliquer si pertinent
alembic upgrade head
```

---

## 📌 Conclusion

**Pour les modifications actuelles** (création de profil après questionnaire) :

✅ **Aucune migration SQL nécessaire**
✅ Les tables existent déjà
✅ Seule la logique applicative a changé

**Il suffit de** :
1. Redémarrer le worker Celery
2. Redémarrer l'API FastAPI
3. Tester le flux signup → questionnaire → profil créé

---

**Date** : 18 novembre 2025  
**Statut** : ✅ Pas de migration requise

