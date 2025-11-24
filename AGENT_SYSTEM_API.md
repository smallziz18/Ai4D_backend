# 🤖 Documentation API - Système Multi-Agents IA

## Vue d'ensemble

Le backend expose **9 agents IA spécialisés** orchestrés par LangGraph avec contexte partagé persistant (PostgreSQL + Redis).

---

## 🎯 Architecture des Agents

### 1. **ProfilerAgent** (Profilage Initial)
- **Rôle** : Analyse du profil utilisateur (niveau, style d'apprentissage, énergie)
- **Sortie** : `estimated_level` (1-10), `learning_style`, `priority_domains`

### 2. **QuestionGeneratorAgent** (Génération Questions)
- **Rôle** : Création de questions adaptatives (QCM, Vrai/Faux, Questions Ouvertes)
- **Focus** : 30% minimum de questions ouvertes (source de vérité pour évaluation)
- **Sortie** : Liste de 10 questions personnalisées

### 3. **EvaluatorAgent** (Évaluation Déterministe)
- **Rôle** : Évaluation stricte avec pondération 70% questions ouvertes / 30% QCM
- **Innovation** : Plafonnement automatique si réponses ouvertes vides (niveau MAX = 2)
- **Sortie** : `niveau_final`, `niveau_label`, `forces`, `faiblesses`

### 4. **TutoringAgent** (Parcours RPG)
- **Rôle** : Création de parcours gamifié (Quêtes, Boss Fights, Skill Tree)
- **Innovation** : Transformation de l'apprentissage en aventure RPG
- **Sortie** : `learning_path` avec XP, badges, milestones

### 5. **RecommendationAgent** (Curation Ressources)
- **Rôle** : Recommandation de ressources externes (vidéos, articles, cours)
- **Innovation** : Pondération selon style d'apprentissage + faiblesses détectées
- **Sortie** : `recommendation_resources` (Top 8 ressources priorisées)
- **Future** : Intégration MCP pour fetch YouTube, arXiv, docs officiels

### 6. **PlanningAgent** (Feuille de Route)
- **Rôle** : Génération de roadmap multi-phases adaptative
- **Innovation** : Ajustement temps réel selon énergie + niveau
- **Sortie** : `learning_roadmap` (4 phases : Fondations → Expansion → Projets → Spécialisation)

### 7. **ProgressionAgent** (Monitoring Continu)
- **Rôle** : Détection précoce de stagnation/régression
- **Innovation** : Intervention proactive avant cristallisation des difficultés
- **Sortie** : `progression_snapshot` (risk_flags, suggested_interventions)

### 8. **VisualizationAgent** (Interface Analytique)
- **Rôle** : Transformation données en structures chart-ready pour frontend
- **Innovation** : Métriques exploitables et motivantes
- **Sortie** : `visualization_payload` (metrics, roadmap_timeline, recommended_tags)

### 9. **ContentGenerationAgent** (Contenu Personnalisé)
- **Rôle** : Production de ressources pédagogiques sur mesure
- **Innovation** : Matériel d'apprentissage adapté aux lacunes spécifiques
- **Sortie** : `generated_content` (explications, exemples, pièges fréquents)

---

## 🔗 Endpoints API (v1)

### **Gestion Sessions**

```http
# Démarrer nouvelle session + génération questions
POST /api/v1/ai/agents/start
Authorization: Bearer {token}

Response:
{
  "session_id": "uuid",
  "questions": [...],
  "user_level_estimated": 5,
  "user_level_label_estimated": "Intermédiaire"
}
```

```http
# Lister sessions utilisateur
GET /api/v1/ai/agents/sessions
Authorization: Bearer {token}

Response:
{
  "sessions": [
    {
      "session_id": "uuid",
      "context_id": "uuid",
      "current_state": "profiling_complete",
      "total_interactions": 12,
      "created_at": "2025-11-22T10:00:00Z"
    }
  ]
}
```

```http
# État complet d'une session
GET /api/v1/ai/agents/sessions/{session_id}
Authorization: Bearer {token}

Response: {state: AgentState} (complet)
```

```http
# Supprimer session
DELETE /api/v1/ai/agents/sessions/{session_id}
Authorization: Bearer {token}

Response: {"deleted": true}
```

### **Soumission Réponses + Analyse Complète**

```http
POST /api/v1/ai/agents/sessions/{session_id}/responses
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "responses": [
    {"numero": 1, "reponse": "A"},
    {"numero": 2, "reponse": "Explication détaillée..."}
  ]
}

Response (Flux complet 9 agents):
{
  "session_id": "uuid",
  "niveau_final": 6.5,
  "niveau_label_final": "Intermédiaire",
  
  "evaluation": {
    "evaluation_globale": {
      "niveau_final": 6.5,
      "niveau_label": "Intermédiaire",
      "moyenne_questions_ouvertes": 6.2,
      "score_qcm_vf": 7.5,
      "open_answered": 4
    },
    "analyse_questions_ouvertes": [...]
  },
  
  "learning_path": {
    "quetes_principales": [...],
    "boss_fights": [...],
    "xp_total": 1500
  },
  
  "learning_roadmap": {
    "phases": [
      {
        "phase": 1,
        "title": "Consolidation des Fondations",
        "duration_weeks": 2,
        "suggested_daily_minutes": 45
      }
    ]
  },
  
  "recommendation_resources": [
    {
      "title": "Guide Fondamental: backpropagation",
      "url": "https://...",
      "source_type": "video",
      "adjusted_score": 0.89,
      "difficulty_fit": "moyen"
    }
  ],
  
  "progression_snapshot": {
    "risk_flags": [],
    "suggested_interventions": []
  },
  
  "visualization_payload": {
    "metrics": {...},
    "roadmap_timeline": [...],
    "recommended_tags": [...]
  },
  
  "generated_content": [
    {
      "concept": "backpropagation",
      "content_type": "explication",
      "raw": "...",
      "estimated_time_min": 8
    }
  ],
  
  "badges_earned": ["Explorateur IA"]
}
```

### **Historique Conversation**

```http
GET /api/v1/ai/agents/sessions/{session_id}/history
Authorization: Bearer {token}

Response:
{
  "conversation_history": [
    {
      "timestamp": "2025-11-22T10:05:00Z",
      "agent": "ProfilerAgent",
      "type": "agent",
      "message": "Analyse de profil : Niveau estimé 5/10"
    }
  ]
}
```

```http
# Ajouter message utilisateur
POST /api/v1/ai/agents/sessions/{session_id}/message
Authorization: Bearer {token}
Content-Type: application/json

Body: {"content": "Message utilisateur"}

Response: {"status": "added", "total_interactions": 13}
```

### **Résumé Simplifié**

```http
GET /api/v1/ai/agents/sessions/{session_id}/summary
Authorization: Bearer {token}

Response:
{
  "session_id": "uuid",
  "summary": {
    "user_level": 6,
    "current_step": "workflow_complete",
    "num_questions": 10,
    "num_responses": 10,
    "is_complete": true
  }
}
```

---

## 🔄 Flux Utilisateur Complet

### **Phase 1 : Inscription + Questions**
1. Frontend : `POST /api/auth/v1/signup` (données de base seulement)
2. Frontend : `POST /api/auth/v1/login`
3. Frontend : `GET /api/profile/v1/me` → 404 (pas de profil)
4. Frontend : Redirige vers `/questionnaire`
5. Frontend : `POST /api/v1/ai/agents/start` → Reçoit questions

### **Phase 2 : Questionnaire**
6. User : Répond aux questions (dont questions ouvertes ⚠️ CRUCIAL)
7. Frontend : `POST /api/v1/ai/agents/sessions/{session_id}/responses`
8. Backend : Exécute **9 agents séquentiels** (5-10 secondes)
9. Frontend : Reçoit analyse complète + parcours RPG

### **Phase 3 : Dashboard**
10. Frontend : `GET /api/profile/v1/me` → 200 (profil créé)
11. Frontend : Affiche dashboard avec:
    - Niveau + Label
    - Roadmap phases
    - Ressources recommandées
    - Contenu personnalisé
    - Badges

---

## 📊 Exemple Réponse Complète (Condensé)

```json
{
  "niveau_final": 6.5,
  "niveau_label_final": "Intermédiaire",
  "evaluation": {
    "moyenne_questions_ouvertes": 6.2,
    "score_qcm_vf": 7.5,
    "forces": ["Bonne compréhension des CNN"],
    "faiblesses": ["Confusion backpropagation"]
  },
  "learning_roadmap": {
    "phases": [
      {"phase": 1, "title": "Consolidation Fondations", "weeks": 2},
      {"phase": 2, "title": "Expansion Conceptuelle", "weeks": 3}
    ]
  },
  "recommendation_resources": [
    {"title": "Vidéo: Backpropagation", "url": "...", "score": 0.89}
  ],
  "visualization_payload": {
    "metrics": {"niveau": 6.5, "moyenne_open": 6.2}
  },
  "generated_content": [
    {"concept": "backpropagation", "content_type": "explication"}
  ]
}
```

---

## 🚀 Intégration Frontend Nuxt.js

### **Composables Recommandés**

```typescript
// composables/useAIAgents.ts
export const useAIAgents = () => {
  const startSession = async () => {
    const { data } = await $fetch('/api/v1/ai/agents/start', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  }

  const submitResponses = async (sessionId: string, responses: any[]) => {
    const { data } = await $fetch(`/api/v1/ai/agents/sessions/${sessionId}/responses`, {
      method: 'POST',
      body: { responses },
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  }

  return { startSession, submitResponses }
}
```

### **Pages Recommandées**

```
pages/
  questionnaire/
    index.vue          → Démarrage session + affichage questions
    [sessionId].vue    → Réponses + soumission
  dashboard/
    index.vue          → Vue globale (niveau, roadmap)
    learning-path.vue  → Parcours RPG détaillé
    resources.vue      → Ressources recommandées
    progress.vue       → Suivi progression
```

---

## 🔮 Évolutions Futures (MCP)

### **Model Context Protocol (MCP)**
- **RecommendationAgent** : Fetch réel YouTube, arXiv, Coursera
- **ContentGenerationAgent** : LLM avancé (GPT-4, Claude) pour contenu riche
- **ProgressionAgent** : Intégration analytics temps réel

### **Endpoints à Ajouter**
```http
POST /api/v1/ai/agents/recommendation/fetch-external
GET /api/v1/ai/agents/content/generate-llm/{concept}
GET /api/v1/ai/agents/progression/analytics/{user_id}
```

---

## 📞 Support

Questions ? Consultez :
- Logs backend : `celery.log`, `uvicorn logs`
- Contexte Redis : `GET /api/v1/ai/agents/sessions/{session_id}/history`
- État complet : `GET /api/v1/ai/agents/sessions/{session_id}`

**Mainteneur** : Équipe Backend AI4D  
**Version** : v1.0 (LangGraph Multi-Agents)

