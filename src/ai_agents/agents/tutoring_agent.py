"""
Agent de tutorat personnalisé - Accompagne l'utilisateur dans son apprentissage.
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from src.config import Config
from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service


TUTORING_SYSTEM_PROMPT = """
Tu es un tuteur IA expert et bienveillant spécialisé en Intelligence Artificielle.

🎯 Ta mission :
Accompagner l'apprenant de manière personnalisée dans son parcours d'apprentissage.

👨‍🏫 Ton rôle :
1. **Expliquer les concepts** de manière adaptée au niveau
2. **Détecter les difficultés** et ajuster l'approche
3. **Donner des exemples concrets** et relatable
4. **Encourager** sans être condescendant
5. **Proposer des exercices** progressifs

🎓 Principes pédagogiques :

**Adaptation au niveau :**
- Débutant (1-3) : Analogies simples, pas de jargon technique
- Intermédiaire (4-6) : Balance théorie/pratique, termes techniques expliqués
- Avancé (7-10) : Discussions approfondies, références papiers de recherche

**Style d'explication :**
- 🔹 Commence toujours par une analogie ou exemple concret
- 🔹 Explique le "pourquoi" avant le "comment"
- 🔹 Donne des exemples de code si pertinent
- 🔹 Propose des visualisations ou schémas
- 🔹 Termine par des exercices pratiques

**Détection de difficultés :**
- Si l'apprenant pose la même question → Changer d'approche pédagogique
- Si l'apprenant est découragé → Encourager et simplifier
- Si l'apprenant est confus → Revenir aux bases

🎮 Gamification :
- Célèbre les progrès (même petits)
- Propose des défis adaptés
- Encourage la curiosité

FORMAT JSON STRICT :
{
  "explication": "Explication détaillée et pédagogique du concept...",
  "analogie": "Analogie concrète pour faciliter la compréhension",
  "exemple_code": "# Code Python illustratif (si pertinent)",
  "points_cles": ["Point 1", "Point 2", "Point 3"],
  "exercices_proposes": [
    {
      "titre": "Exercice 1",
      "description": "...",
      "difficulte": "facile|moyen|difficile",
      "temps_estime": "15 minutes"
    }
  ],
  "ressources_complementaires": [
    {
      "titre": "Vidéo YouTube recommandée",
      "url": "https://...",
      "type": "video|article|cours"
    }
  ],
  "prochaine_etape": "Suggestion pour la suite de l'apprentissage",
  "encouragement": "Message motivant personnalisé"
}
"""


class TutoringAgent:
    """Agent de tutorat personnalisé."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.7  # Créativité pour explications variées
        )
        self.name = "TutoringAgent"

    async def explain_concept(
        self,
        concept: str,
        user_level: int,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Explique un concept de manière adaptée au niveau de l'utilisateur.

        Args:
            concept: Le concept à expliquer
            user_level: Niveau de l'utilisateur (1-10)
            user_context: Contexte utilisateur (compétences, objectifs, etc.)

        Returns:
            Dict avec explication détaillée et ressources
        """
        user_context = user_context or {}

        # Déterminer le style d'explication selon le niveau
        if user_level <= 3:
            style = "très simple, avec des analogies du quotidien"
            profondeur = "concepts de base uniquement"
        elif user_level <= 6:
            style = "équilibré entre théorie et pratique"
            profondeur = "concepts intermédiaires avec exemples de code"
        else:
            style = "technique et approfondi"
            profondeur = "détails d'implémentation et optimisations"

        # Récupérer les compétences et objectifs
        competences = user_context.get("competences", [])
        objectifs = user_context.get("objectifs", "")

        context_str = f"""
PROFIL APPRENANT :
- Niveau : {user_level}/10
- Compétences actuelles : {', '.join(competences) if competences else 'Aucune'}
- Objectifs : {objectifs or 'Non définis'}

STYLE D'EXPLICATION SOUHAITÉ : {style}
PROFONDEUR : {profondeur}
"""

        messages = [
            SystemMessage(content=TUTORING_SYSTEM_PROMPT),
            HumanMessage(content=f"""
{context_str}

L'apprenant souhaite comprendre : **{concept}**

Explique ce concept de manière pédagogique et adaptée à son niveau.
Retourne un JSON avec :
- Explication détaillée
- Analogie concrète
- Exemple de code (si pertinent)
- Points clés à retenir
- Exercices pratiques
- Ressources complémentaires
- Message d'encouragement
            """)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parser JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            explanation = json.loads(response_text)

            return {
                "status": "success",
                "concept": concept,
                "niveau_apprenant": user_level,
                **explanation
            }

        except Exception as e:
            print(f"❌ Erreur explication concept: {e}")
            return {
                "status": "error",
                "concept": concept,
                "explication": f"Impossible d'expliquer le concept pour le moment. Erreur: {str(e)}",
                "analogie": "",
                "exemple_code": "",
                "points_cles": [],
                "exercices_proposes": [],
                "ressources_complementaires": [],
                "prochaine_etape": "Réessayer plus tard",
                "encouragement": "Continue ton apprentissage !"
            }

    async def suggest_exercises(
        self,
        topic: str,
        difficulty: str,
        user_level: int
    ) -> List[Dict[str, Any]]:
        """
        Suggère des exercices pratiques adaptés.

        Args:
            topic: Sujet des exercices
            difficulty: Difficulté souhaitée (facile, moyen, difficile)
            user_level: Niveau de l'utilisateur

        Returns:
            Liste d'exercices avec descriptions et temps estimé
        """
        messages = [
            SystemMessage(content=TUTORING_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Propose 3 exercices pratiques sur le sujet : **{topic}**

Niveau de l'apprenant : {user_level}/10
Difficulté souhaitée : {difficulty}

Pour chaque exercice, fournis :
- Titre clair et engageant
- Description détaillée de ce qu'il faut faire
- Objectif pédagogique
- Temps estimé
- Indices pour démarrer

Retourne un JSON :
{{
  "exercices": [
    {{
      "titre": "...",
      "description": "...",
      "objectif": "...",
      "difficulte": "{difficulty}",
      "temps_estime": "...",
      "indices": ["Indice 1", "Indice 2"],
      "technologies": ["Python", "scikit-learn", "..."]
    }}
  ]
}}
            """)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            return result.get("exercices", [])

        except Exception as e:
            print(f"❌ Erreur génération exercices: {e}")
            return []

    async def detect_difficulties(
        self,
        user_id: str,
        session_id: str,
        recent_interactions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Détecte les difficultés d'apprentissage basées sur l'historique.

        Args:
            user_id: ID de l'utilisateur
            session_id: ID de session
            recent_interactions: Historique récent des interactions

        Returns:
            Dict avec difficultés détectées et recommandations
        """
        # Récupérer le contexte
        context = await shared_context_service.get_or_create_context(user_id, session_id)

        if not context:
            return {
                "difficulties_detected": False,
                "message": "Pas assez de données pour détecter des difficultés"
            }

        conversation_history = context.get("conversation_history", [])

        # Analyser l'historique
        repeated_topics = []
        confusion_signals = []

        # Détecter les sujets qui reviennent (difficultés potentielles)
        topic_counts = {}
        for msg in conversation_history[-20:]:  # 20 derniers messages
            content = msg.get("content", "").lower()

            # Mots-clés de confusion
            if any(word in content for word in ["je ne comprends pas", "confus", "difficile", "compliqué"]):
                confusion_signals.append(msg)

            # Compter les sujets récurrents
            topics = ["backpropagation", "cnn", "rnn", "transformer", "gradient", "overfitting"]
            for topic in topics:
                if topic in content:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # Identifier les sujets problématiques (> 2 mentions)
        for topic, count in topic_counts.items():
            if count >= 2:
                repeated_topics.append(topic)

        if repeated_topics or confusion_signals:
            return {
                "difficulties_detected": True,
                "repeated_topics": repeated_topics,
                "confusion_signals": len(confusion_signals),
                "recommendation": "Adapter l'approche pédagogique",
                "suggested_actions": [
                    f"Revoir les bases de : {', '.join(repeated_topics)}" if repeated_topics else "",
                    "Utiliser plus d'analogies et d'exemples concrets",
                    "Proposer des exercices guidés pas à pas",
                    "Encourager à poser des questions plus spécifiques"
                ]
            }
        else:
            return {
                "difficulties_detected": False,
                "message": "L'apprentissage se déroule bien",
                "encouragement": "Continue comme ça ! 🎉"
            }

    async def tutor(self, state: AgentState) -> Dict[str, Any]:
        """
        Point d'entrée principal du tutoring agent dans le workflow.

        Args:
            state: État actuel du workflow

        Returns:
            Mises à jour à appliquer à l'état
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        user_level = state.get("user_level", 5)
        user_profile = state.get("user_profile", {})

        # Détecter les difficultés
        difficulties = await self.detect_difficulties(user_id, session_id)

        # Logging
        await shared_context_service.add_message(
            user_id,
            session_id,
            self.name,
            f"Analyse des difficultés : {difficulties.get('message', 'Aucune difficulté détectée')}"
        )

        # Préparer les recommandations de tutorat
        tutorials = []

        # Si difficultés détectées, proposer aide ciblée
        if difficulties.get("difficulties_detected"):
            for topic in difficulties.get("repeated_topics", []):
                explanation = await self.explain_concept(
                    concept=topic,
                    user_level=user_level,
                    user_context=user_profile
                )
                tutorials.append(explanation)

        return {
            "tutoring_analysis": difficulties,
            "tutorials": tutorials,
            "current_step": "tutoring_complete",
            "next_step": "recommendation"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Permet d'utiliser l'agent comme une fonction (requis par LangGraph)."""
        import asyncio
        return asyncio.run(self.tutor(state))


# Instance globale
tutoring_agent = TutoringAgent()
