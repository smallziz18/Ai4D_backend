"""
Agent Chatbot - Assistant conversationnel avec contexte utilisateur persistant.
"""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
import json
from datetime import datetime, UTC

from src.config import Config
from src.ai_agents.shared_context import shared_context_service


CHATBOT_SYSTEM_PROMPT = """
Tu es un assistant pédagogique IA expert et bienveillant qui aide les apprenants dans leur parcours d'apprentissage.

🎯 Ton rôle :
- Répondre aux questions sur l'IA/ML/DL avec clarté et pédagogie
- Adapter tes explications au niveau de l'apprenant
- Encourager et motiver l'apprenant
- Suggérer des ressources pertinentes
- Clarifier les concepts difficiles avec des exemples concrets
- Guider sans donner toutes les réponses (favoriser l'apprentissage actif)

📊 CONTEXTE UTILISATEUR DISPONIBLE :
Tu as accès au profil complet de l'utilisateur :
- Niveau actuel
- Forces et faiblesses
- Cours en cours
- Progression
- Historique des conversations

🎨 STYLE DE COMMUNICATION :
- Utilise des emojis pour rendre la conversation vivante 🎯 ✨ 🚀
- Sois encourageant et positif
- Donne des exemples concrets et des analogies
- Structure tes réponses clairement
- Pose des questions pour vérifier la compréhension

💡 APPROCHE PÉDAGOGIQUE :
1. **Socratique** : Pose des questions pour faire réfléchir
2. **Exemples** : Illustre avec des cas concrets
3. **Progression** : Du simple au complexe
4. **Pratique** : Encourage à coder/expérimenter
5. **Liens** : Relie aux concepts déjà maîtrisés

⚠️ RÈGLES IMPORTANTES :
- Ne donne JAMAIS directement les réponses aux exercices
- Encourage la recherche et l'expérimentation
- Si la question est hors sujet, ramène gentiment vers l'apprentissage
- Si tu ne sais pas, admets-le et suggère des ressources
- Adapte ton niveau de détail au niveau de l'apprenant

🔍 DÉTECTION D'INTENTION :
- Question de concept → Explication pédagogique
- Problème de code → Guidage sans solution directe
- Motivation basse → Encouragement et remotivation
- Confusion → Clarification et simplification
- Besoin de ressources → Recommandations pertinentes
"""


class ChatbotAgent:
    """
    Agent conversationnel contextuel pour assistance pédagogique.
    Maintient l'historique des conversations et adapte ses réponses.
    """

    def __init__(self):
        # Lazy init pour éviter les problèmes de fork dans Celery
        self.llm = None
        self.name = "ChatbotAgent"

    async def chat(
        self,
        user_id: str,
        session_id: str,
        message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Gérer une conversation avec contexte.

        Args:
            user_id: ID de l'utilisateur
            session_id: ID de session
            message: Message de l'utilisateur
            user_context: Contexte utilisateur (profil, progression, etc.)

        Returns:
            Réponse avec contexte et métadonnées
        """
        try:
            # Initialiser le LLM à la première utilisation (dans le bon process)
            if self.llm is None:
                self.llm = ChatOpenAI(
                    model="gpt-4o",
                    api_key=Config.OPENAI_API_KEY,
                    temperature=0.7
                )

            # Récupérer le contexte partagé
            context = await shared_context_service.get_or_create_context(user_id, session_id)

            # Récupérer l'historique récent de conversation
            conversation_history = context.get("conversation_history", [])[-10:] if context else []

            # Construire le contexte utilisateur
            if not user_context:
                context_data = context.get("context_data", {}) if context else {}
                user_context = context_data.get("user_profile", {})

            user_level = user_context.get("niveau_technique", 5)
            current_courses = user_context.get("current_courses", [])
            strengths = user_context.get("strengths", [])
            weaknesses = user_context.get("weaknesses", [])
            learning_path = user_context.get("learning_path", {})

            # Construire le contexte complet
            context_str = f"""
PROFIL APPRENANT :
- Niveau : {user_level}/10
- Forces : {', '.join(strengths) if strengths else 'Non identifiées'}
- Faiblesses : {', '.join(weaknesses) if weaknesses else 'Non identifiées'}
- Cours actifs : {len(current_courses)} cours en cours
- Parcours : {learning_path.get('titre', 'Non défini')}

PROGRESSION ACTUELLE :
{json.dumps(user_context.get('progression', {}), indent=2, ensure_ascii=False)}
"""

            # Construire les messages pour le LLM
            messages: List[BaseMessage] = [SystemMessage(content=CHATBOT_SYSTEM_PROMPT)]

            # Ajouter le contexte utilisateur
            messages.append(SystemMessage(content=f"CONTEXTE UTILISATEUR:\n{context_str}"))

            # Ajouter l'historique de conversation
            for hist in conversation_history[-5:]:  # 5 derniers échanges
                if hist.get("role") == "user":
                    messages.append(HumanMessage(content=hist.get("content", "")))
                elif hist.get("role") == "assistant":
                    messages.append(AIMessage(content=hist.get("content", "")))

            # Ajouter le message actuel
            messages.append(HumanMessage(content=message))

            # Obtenir la réponse
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Analyser l'intention de la question
            intention = await self._detect_intention(message, user_level)

            # Sauvegarder dans l'historique
            await shared_context_service.add_message(
                user_id,
                session_id,
                "user",
                message,
                message_type="chat"
            )

            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                response_text,
                message_type="chat"
            )

            # Mettre à jour les métriques d'engagement
            total_interactions = context.get("total_interactions", 0) if context else 0
            await shared_context_service.update_context(
                user_id,
                session_id,
                {
                    "total_interactions": total_interactions + 1,
                    "last_chat_timestamp": datetime.now(UTC).isoformat()
                }
            )

            return {
                "response": response_text,
                "intention": intention,
                "conversation_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "suggestions": await self._generate_suggestions(intention, user_context)
            }

        except Exception as e:
            error_msg = f"Erreur dans ChatbotAgent: {str(e)}"
            print(error_msg)  # Log l'erreur
            import traceback
            traceback.print_exc()  # Log la stack trace complète

            return {
                "response": "Désolé, j'ai rencontré un problème. Peux-tu reformuler ta question ? 🤔",
                "intention": {
                    "primary": "error",
                    "confidence": 0.0,
                    "all_intentions": {},
                    "error": error_msg
                },
                "conversation_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "suggestions": [
                    "💬 Reformule ta question",
                    "📚 Voir mes cours",
                    "📊 Voir ma progression"
                ]
            }

    async def _detect_intention(self, message: str, user_level: int) -> Dict[str, Any]:
        """
        Détecter l'intention de la question.
        """
        message_lower = message.lower()

        intentions = {
            "concept_question": any(word in message_lower for word in ["qu'est-ce", "comment", "pourquoi", "expliquer", "définir"]),
            "code_help": any(word in message_lower for word in ["code", "erreur", "bug", "implémenter", "fonction"]),
            "resource_request": any(word in message_lower for word in ["ressource", "cours", "tutoriel", "livre", "vidéo", "recommander"]),
            "motivation": any(word in message_lower for word in ["difficile", "bloqué", "abandonner", "démotivé", "dur"]),
            "evaluation": any(word in message_lower for word in ["évaluation", "test", "quiz", "prêt", "vérifier"]),
            "progression": any(word in message_lower for word in ["progrès", "niveau", "où j'en suis", "avancer"])
        }

        primary_intention = max(intentions.items(), key=lambda x: x[1])

        return {
            "primary": primary_intention[0],
            "confidence": 0.8 if primary_intention[1] else 0.3,
            "all_intentions": {k: v for k, v in intentions.items() if v}
        }

    async def _generate_suggestions(
        self,
        intention: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> List[str]:
        """
        Générer des suggestions de questions de suivi.
        """
        primary = intention.get("primary", "concept_question")

        suggestions_map = {
            "concept_question": [
                "💡 Peux-tu me donner un exemple concret ?",
                "📊 Montre-moi un cas d'utilisation",
                "🔗 Quel est le lien avec ce que j'ai déjà appris ?"
            ],
            "code_help": [
                "🔍 Où se trouve exactement l'erreur ?",
                "💻 Montre-moi comment déboguer",
                "📝 Quelles sont les bonnes pratiques ?"
            ],
            "resource_request": [
                "📚 Quelles ressources pour mon niveau ?",
                "🎥 Y a-t-il des vidéos recommandées ?",
                "💼 Des projets pratiques à faire ?"
            ],
            "motivation": [
                "🎯 Quels sont mes progrès jusqu'ici ?",
                "⚡ Comment rester motivé ?",
                "🏆 Quels sont mes prochains objectifs ?"
            ],
            "evaluation": [
                "📝 Lancer une évaluation",
                "📊 Voir ma progression détaillée",
                "🎯 Quelles compétences dois-je améliorer ?"
            ],
            "progression": [
                "📈 Voir mon tableau de bord",
                "🎯 Mes prochaines quêtes",
                "🏆 Mes badges et réalisations"
            ]
        }

        return suggestions_map.get(primary, [
            "💬 Pose-moi une question",
            "📚 Voir mes cours",
            "📊 Voir ma progression"
        ])

    async def get_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Récupérer l'historique de conversation.
        """
        try:
            context = await shared_context_service.get_context(user_id, session_id)
            if not context:
                return []

            history = context.conversation_history[-limit:]

            # Filtrer uniquement les messages de chat
            chat_history = [
                msg for msg in history
                if msg.get("message_type") == "chat"
            ]

            return chat_history

        except Exception as e:
            print(f"Erreur récupération historique: {e}")
            return []


# Instance globale
chatbot_agent = ChatbotAgent()
