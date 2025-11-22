# Guide de Test Rapide - Questionnaire Initial

## 🚀 Démarrage

### 1. Lancer les services nécessaires

```bash
# Terminal 1 - Backend API
cd /Users/smallziz/Documents/project\ ai4d/backend_ai4_d
uvicorn src.main:app --reload --port 8000

# Terminal 2 - Celery Worker
cd /Users/smallziz/Documents/project\ ai4d/backend_ai4_d
celery -A src.celery_tasks worker --loglevel=info

# Terminal 3 - MongoDB (si pas déjà lancé)
# Vérifier que MongoDB tourne sur le port par défaut (27017)
```

## 🧪 Option 1 : Test avec Script Python

```bash
# Éditer le script pour mettre votre UUID utilisateur
nano test_questionnaire_initial.py
# Remplacer : test_user_id = "votre-uuid-ici"

# Lancer le test
python test_questionnaire_initial.py
```

**Résultat attendu :**
```
✅ Questionnaire initial sauvegardé avec succès !
📊 Résultats de la sauvegarde :
   - Questionnaire complété : True
   - Nombre de réponses : 8
   - Compétences identifiées : 5
   - Recommandations : 5
```

## 🌐 Option 2 : Test avec curl/HTTPie

### A. Obtenir un token d'authentification

```bash
# Se connecter
curl -X POST http://localhost:8000/api/auth/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=votre_email@example.com&password=votre_password"

# Récupérer le token depuis la réponse
# Exemple : {"access_token": "eyJ...", "token_type": "bearer"}
```

### B. Envoyer le questionnaire initial

```bash
# Remplacer YOUR_TOKEN par le token obtenu
curl -X POST http://localhost:8000/api/profile/v1/analyze_quiz \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_data_questionnaire_initial.json

# Réponse attendue :
# {
#   "task_id": "abc-123-def",
#   "is_initial_questionnaire": true,
#   "message": "Questionnaire initial en cours d'analyse"
# }
```

### C. Vérifier le statut de l'analyse

```bash
# Remplacer TASK_ID par l'ID retourné ci-dessus
curl http://localhost:8000/api/profile/v1/analysis_result/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# Attendre que status = "success"
```

### D. Vérifier le profil sauvegardé

```bash
# 1. Profil complet
curl http://localhost:8000/api/profile/v1/me \
  -H "Authorization: Bearer YOUR_TOKEN" | jq

# Vérifier :
# - questionnaire_initial_complete: true
# - questionnaire_reponses: [...]
# - analyse_questions_ouvertes: {...}
# - recommandations: [...]

# 2. Recommandations
curl http://localhost:8000/api/profile/v1/recommendations \
  -H "Authorization: Bearer YOUR_TOKEN" | jq

# Devrait retourner 200 avec :
# {
#   "recommendations": [...],
#   "questionnaire_complete": true,
#   "analyse_questions_ouvertes": {...}
# }
```

## 🗄️ Option 3 : Vérification directe dans MongoDB

```bash
# Se connecter à MongoDB
mongosh

# Sélectionner la base de données
use ai4d

# Afficher tous les profils avec questionnaire complété
db.profils.find(
  { "questionnaire_initial_complete": true }
).pretty()

# Vérifier un profil spécifique
db.profils.findOne(
  { "utilisateur_id": "votre-uuid-ici" },
  {
    questionnaire_initial_complete: 1,
    questionnaire_initial_date: 1,
    questionnaire_reponses: 1,
    analyse_questions_ouvertes: 1,
    recommandations: 1,
    competences: 1,
    niveau: 1
  }
).pretty()
```

## ✅ Checklist de Vérification

Après le questionnaire initial, vérifier que :

- [ ] `questionnaire_initial_complete = true`
- [ ] `questionnaire_initial_date` est définie
- [ ] `questionnaire_reponses` contient toutes les réponses (8 dans notre exemple)
- [ ] `analyse_questions_ouvertes` contient :
  - [ ] `nombre_questions_ouvertes`
  - [ ] `analyse_llm` avec scores et évaluations
  - [ ] `evaluation_detaillee` avec niveau réel estimé
- [ ] `recommandations` contient 3-5 recommandations personnalisées
- [ ] `competences` liste les compétences identifiées
- [ ] `objectifs` et `motivation` sont remplis (si fournis par le LLM)
- [ ] GET `/api/profile/v1/me` retourne **200** (pas 404)
- [ ] GET `/api/profile/v1/recommendations` retourne **200** (pas 404)

## 🐛 Troubleshooting

### Erreur 404 sur /me ou /recommendations

```bash
# Vérifier que le profil existe dans MongoDB
mongosh
> use ai4d
> db.profils.findOne({"utilisateur_id": "votre-uuid"})

# Si null → le profil n'existe pas, créer un profil d'abord
curl -X POST http://localhost:8000/api/profile/v1/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "niveau": 1,
    "xp": 0,
    "badges": [],
    "competences": [],
    "energie": 5
  }'
```

### Erreur "Le questionnaire initial a déjà été complété"

```bash
# Réinitialiser pour tester à nouveau
mongosh
> use ai4d
> db.profils.updateOne(
    {"utilisateur_id": "votre-uuid"},
    {$set: {"questionnaire_initial_complete": false}}
  )
```

### Celery Worker ne démarre pas

```bash
# Vérifier que Redis/RabbitMQ tourne (selon votre config)
# Par défaut avec Redis :
redis-cli ping
# Devrait retourner : PONG

# Vérifier les logs Celery pour plus de détails
celery -A src.celery_tasks worker --loglevel=debug
```

### LLM timeout ou erreur

```bash
# Vérifier la clé API OpenAI
echo $OPENAI_API_KEY

# Ou dans .env
cat .env | grep OPENAI_API_KEY

# Tester l'API directement
python -c "
from src.config import Config
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini', api_key=Config.OPENAI_API_KEY)
print(llm.invoke('Hello').content)
"
```

## 📊 Exemple de Réponse Réussie

### GET /api/profile/v1/me

```json
{
  "id": "673ab8e8d41c6c40ac8f0e84",
  "utilisateur_id": "b935c266-caf0-42e3-87f6-dd1788cd0fc1",
  "niveau": 8,
  "xp": 0,
  "badges": [],
  "competences": [
    "Deep Learning",
    "Backpropagation",
    "CNN",
    "RNN",
    "Transformers"
  ],
  "objectifs": "Approfondir les architectures Transformer et explorer le reinforcement learning avancé",
  "motivation": "Forte motivation démontrée par la qualité des explications",
  "energie": 9,
  "questionnaire_initial_complete": true,
  "questionnaire_initial_date": "2025-11-18T10:30:00",
  "recommandations": [
    "🚀 Excellent niveau ! Prêt pour des concepts avancés",
    "📚 Approfondis les architectures Transformer",
    "💪 Pratique avec des projets de NLP modernes",
    "🎯 Explore le Reinforcement Learning",
    "🔍 Optimise tes modèles"
  ]
}
```

### GET /api/profile/v1/recommendations

```json
{
  "recommendations": [
    "🚀 Excellent niveau ! Prêt pour des concepts avancés",
    "📚 Approfondis les architectures Transformer",
    "💪 Pratique avec des projets de NLP modernes",
    "🎯 Explore le Reinforcement Learning",
    "🔍 Optimise tes modèles"
  ],
  "total": 5,
  "questionnaire_complete": true,
  "niveau": 8,
  "competences": ["Deep Learning", "Backpropagation", "CNN", "RNN", "Transformers"],
  "objectifs": "Approfondir les architectures Transformer...",
  "analyse_questions_ouvertes": {
    "niveau_reel": "avancé",
    "comprehension_profonde": "excellente",
    "capacite_explication": "excellente"
  }
}
```

## 🎯 Prochaines Étapes

Une fois les tests réussis :

1. ✅ Intégrer avec le frontend Streamlit
2. ✅ Afficher le dashboard avec les recommandations
3. ✅ Permettre à l'utilisateur de consulter son analyse détaillée
4. ✅ Proposer des parcours d'apprentissage basés sur le profil

---

**Note :** Ce guide suppose que MongoDB et tous les services sont configurés correctement selon le fichier `docker-compose.yml` ou votre configuration locale.

