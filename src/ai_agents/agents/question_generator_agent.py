"""
Agent générateur de questions - Génère des questions adaptées au profil.
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from src.config import Config
from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service


QUESTION_GENERATOR_SYSTEM_PROMPT = """
Tu es un générateur expert de questions sur l'INTELLIGENCE ARTIFICIELLE uniquement.

RÈGLE ABSOLUE:
- INTERDICTION des questions Vrai/Faux. Ne JAMAIS produire de type "VraiOuFaux".
- Types autorisés: ChoixMultiple, QuestionOuverte, ListeOuverte.
- Minimum 40% de questions ouvertes (QuestionOuverte + ListeOuverte).

Génère des questions IA adaptées au niveau de l'utilisateur, en évitant la mémorisation et en favorisant la compréhension.
"""


class QuestionGeneratorAgent:
    """
    Agent de génération de questions adaptatives.
    Génère des questions basées sur le profil et la stratégie d'apprentissage.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.7  # Créativité modérée pour variété
        )
        self.name = "QuestionGeneratorAgent"

    async def generate_questions(
        self,
        state: AgentState,
        num_questions: int = 10
    ) -> Dict[str, Any]:
        """
        Générer des questions adaptées au profil utilisateur.

        Args:
            state: État actuel du workflow
            num_questions: Nombre de questions à générer

        Returns:
            Mises à jour à appliquer à l'état
        """
        user_profile = state.get("user_profile", {})
        user_level = state.get("user_level", 5)
        profiler_analysis = state.get("meta_data", {}).get("profiler_analysis", {})
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        # Récupérer la stratégie de profilage
        priority_domains = profiler_analysis.get("priority_domains", ["machine_learning"])
        learning_style = profiler_analysis.get("learning_style", "balanced")

        # Construire le contexte
        context = {
            "niveau": user_level,
            "domaines_prioritaires": priority_domains,
            "style_apprentissage": learning_style,
            "competences_actuelles": state.get("user_competences", []),
            "objectifs": state.get("user_objectifs", "")
        }

        context_json = json.dumps(context, indent=2, ensure_ascii=False)

        messages = [
            SystemMessage(content=QUESTION_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Génère {num_questions} questions d'évaluation IA adaptées à ce profil :

CONTEXTE UTILISATEUR :
{context_json}

CONTRAINTES :
- {num_questions} questions au total
- Au moins 40% de questions ouvertes (QuestionOuverte + ListeOuverte)
- Adapter la difficulté au niveau {user_level}/10
- Prioriser les domaines : {', '.join(priority_domains)}
- Style d'apprentissage : {learning_style}

TYPES à inclure (exemple pour 10 questions) :
- 6 ChoixMultiple
- 3 QuestionOuverte
- 1 ListeOuverte

Génère maintenant les questions en JSON uniquement (pas de texte avant/après).
            """)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Nettoyer et parser JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            questions = json.loads(response_text)

            # Validation basique
            if not isinstance(questions, list) or len(questions) == 0:
                raise ValueError("Format de questions invalide")

            # Supprimer/convertir toute question VraiOuFaux résiduelle
            cleaned_questions = []
            for q in questions:
                if q.get("type") == "VraiOuFaux":
                    q["type"] = "ChoixMultiple"
                    q["options"] = [
                        "A. Oui",
                        "B. Non",
                        "C. Ça dépend",
                        "D. Je ne sais pas"
                    ]
                    corr = q.get("correction") or "Réponse attendue selon le contexte"
                    if isinstance(corr, str) and corr and not corr.startswith(("A", "B", "C", "D")):
                        q["correction"] = f"A - {corr}"
                cleaned_questions.append(q)

            # Compter les questions ouvertes
            open_questions = [q for q in cleaned_questions if q.get("type") in ["QuestionOuverte", "ListeOuverte"]]
            open_percentage = len(open_questions) / len(cleaned_questions) * 100

            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                f"Généré {len(cleaned_questions)} questions (dont {len(open_questions)} ouvertes - {open_percentage:.0f}%)"
            )

            # Enregistrer la décision
            decision = {
                "agent": self.name,
                "timestamp": state.get("updated_at"),
                "decision": "questions_generated",
                "details": {
                    "num_questions": len(cleaned_questions),
                    "num_open_questions": len(open_questions),
                    "open_percentage": open_percentage
                }
            }

            return {
                "questions": cleaned_questions,
                "agent_decisions": state.get("agent_decisions", []) + [decision],
                "current_step": "questions_generated",
                "next_step": "awaiting_responses"
            }

        except Exception as e:
            error_msg = f"Erreur dans QuestionGeneratorAgent: {str(e)}"

            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                error_msg,
                message_type="system"
            )

            return {
                "error_message": error_msg,
                "needs_human_review": True
            }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Permet d'utiliser l'agent comme une fonction"""
        import asyncio
        return asyncio.run(self.generate_questions(state))


# Instance globale
question_generator_agent = QuestionGeneratorAgent()

