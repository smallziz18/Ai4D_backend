# 🧪 Tests du Questionnaire Initial

## Scénario de Test Complet

### 1. Vérifier le statut initial
```bash
curl -X GET "http://localhost:8000/api/profile/v1/questionnaire/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Attendu** : `questionnaire_complete: false`

---

### 2. Soumettre le questionnaire initial via analyze_quiz

```bash
curl -X POST "http://localhost:8000/api/profile/v1/analyze_quiz" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "questions_data": [
      {
        "question": "Expliquez ce qu'\''est l'\''apprentissage supervisé en IA",
        "type": "ouverte",
        "user_answer": "L'\''apprentissage supervisé est une méthode où le modèle apprend à partir de données étiquetées. On fournit des exemples avec les réponses correctes, et le modèle apprend à faire des prédictions sur de nouvelles données.",
        "correction": "Bonne explication générale"
      },
      {
        "question": "Quelle est la différence entre classification et régression ?",
        "type": "ouverte",
        "user_answer": "La classification prédit des catégories (oui/non, chat/chien), tandis que la régression prédit des valeurs continues (prix, température).",
        "correction": "Excellente distinction"
      },
      {
        "question": "Le deep learning fait partie du machine learning ?",
        "type": "vrai_faux",
        "user_answer": "Vrai",
        "is_correct": true,
        "correction": "Vrai - Le DL est une sous-branche du ML"
      },
      {
        "question": "Quel algorithme utilise-t-on pour la classification ?",
        "type": "qcm",
        "user_answer": "A",
        "is_correct": true,
        "correction": "A - Decision Tree, Random Forest, SVM, etc."
      }
    ],
    "score": 85
  }'
```

**Attendu** : 
```json
{
  "task_id": "xxx-yyy-zzz",
  "is_initial_questionnaire": true,
  "message": "Questionnaire initial en cours d'analyse"
}
```

---

### 3. Vérifier le résultat de l'analyse

```bash
# Remplacer TASK_ID par la valeur reçue
curl -X GET "http://localhost:8000/api/profile/v1/analysis_result/TASK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Attendu** :
```json
{
  "status": "success",
  "result": {
    "ok": true,
    "type": "initial_questionnaire",
    "questionnaire_complete": true,
    "questions_ouvertes_analysees": 2,
    "analyse_llm": {
      "comprehension_profonde": "elevee",
      "capacite_explication": "bonne",
      "niveau_reel": "intermediaire",
      "competences": ["ML", "Classification", "Regression"],
      ...
    }
  }
}
```

---

### 4. Vérifier le statut après soumission

```bash
curl -X GET "http://localhost:8000/api/profile/v1/questionnaire/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Attendu** : `questionnaire_complete: true` ✅

---

### 5. Récupérer le profil

```bash
curl -X GET "http://localhost:8000/api/profile/v1/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Attendu** : Profil complet avec :
- `questionnaire_initial_complete: true`
- `competences` rempli
- `objectifs` rempli

---

### 6. Récupérer les recommandations

```bash
curl -X GET "http://localhost:8000/api/profile/v1/recommendations" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Attendu** : Recommandations basées sur l'analyse des questions ouvertes

---

### 7. Récupérer les résultats détaillés

```bash
curl -X GET "http://localhost:8000/api/profile/v1/questionnaire/results" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Attendu** : Toutes les réponses + analyse complète

---

### 8. Tenter de refaire le questionnaire (doit échouer)

```bash
curl -X POST "http://localhost:8000/api/profile/v1/analyze_quiz" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "questions_data": [...],
    "score": 90
  }'
```

**Attendu** : 
- `is_initial_questionnaire: false` (sera traité comme quiz normal)
- OU erreur si on utilise `/questionnaire/submit`

---

## Vérifications MongoDB

### Structure du document profil

```javascript
db.profils.findOne({"utilisateur_id": "USER_UUID"})
```

**Doit contenir** :
```javascript
{
  "questionnaire_initial_complete": true,
  "questionnaire_initial_date": ISODate("..."),
  "questionnaire_reponses": [
    {
      "question": "...",
      "type": "ouverte",
      "reponse_utilisateur": "...",
      "poids_evaluation": "élevé"
    }
  ],
  "analyse_questions_ouvertes": {
    "nombre_questions_ouvertes": 2,
    "evaluation_detaillee": {
      "comprehension_profonde": "elevee",
      "capacite_explication": "bonne",
      "niveau_reel_estime": "intermediaire"
    }
  },
  "competences": ["ML", "Classification", ...],
  "objectifs": "...",
  "motivation": "..."
}
```

---

## Points Clés à Vérifier ✅

1. ✅ Le questionnaire initial est détecté automatiquement
2. ✅ Les données sont stockées dans MongoDB
3. ✅ Les questions ouvertes sont analysées par le LLM
4. ✅ Le profil est mis à jour avec compétences/objectifs
5. ✅ Les endpoints `/me` et `/recommendations` fonctionnent
6. ✅ On ne peut faire le questionnaire qu'une seule fois
7. ✅ Les quiz suivants sont traités normalement (gamification)

---

## Logs à Surveiller

```
[PROFILE_ANALYSIS] Starting analysis for user: username
[PROFILE_ANALYSIS] Is initial questionnaire: True
[PROFILE_ANALYSIS] Found 2 open-ended questions
[PROFILE_ANALYSIS] Performing deep LLM analysis on open-ended questions...
[PROFILE_ANALYSIS] LLM analysis successful: intermediaire level detected
[PROFILE_ANALYSIS] Saving initial questionnaire to MongoDB...
[PROFILE_ANALYSIS] Initial questionnaire saved successfully
```

---

## Débogage

Si le questionnaire n'est pas sauvegardé :

1. Vérifier les logs Celery
2. Vérifier que `is_initial_questionnaire=True` dans la tâche
3. Vérifier MongoDB : `db.profils.findOne({...})`
4. Vérifier que le LLM est accessible
5. Vérifier les erreurs dans `analysis_result`

---

## Format des Questions

### Question Ouverte (prioritaire ⭐)
```json
{
  "question": "Expliquez...",
  "type": "ouverte",  // ou "open", "text", "essay"
  "user_answer": "Réponse longue et détaillée...",
  "correction": "Ce qui est attendu"
}
```

### Question Fermée (QCM, Vrai/Faux)
```json
{
  "question": "Le ML est-il...",
  "type": "vrai_faux",  // ou "qcm"
  "user_answer": "Vrai",
  "is_correct": true,
  "correction": "Vrai - explication"
}
```

Les **questions ouvertes ont un poids plus élevé** dans l'évaluation du niveau réel !

