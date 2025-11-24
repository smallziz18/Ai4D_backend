"""
Agent de profilage - Analyse le profil utilisateur et adapte l'expérience.
Utilise LangGraph pour orchestration et contexte partagé.
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from src.config import Config
from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service


PROFILER_SYSTEM_PROMPT = """
Tu es un expert en profilage d'apprenants IA.

🎯 Ta mission :
1. Analyser le profil utilisateur (niveau, compétences, objectifs, motivation)
2. Identifier le style d'apprentissage (visuel, pratique, théorique, etc.)
3. Détecter les lacunes et forces potentielles
4. Proposer une stratégie d'apprentissage personnalisée

📊 Analyse à faire :
- Niveau technique réel (1-10)
- Domaines IA à prioriser
- Type de questions à poser (conceptuelles vs pratiques)
- Rythme d'apprentissage recommandé

⚠️ PRINCIPE FONDAMENTAL :
Les questions ouvertes sont LA SOURCE DE VÉRITÉ pour évaluer le vrai niveau.
Un utilisateur qui excelle aux QCM mais échoue aux questions ouvertes est un DÉBUTANT.

Réponds TOUJOURS en JSON avec cette structure :
{
    "estimated_level": 5,
    "learning_style": "practical",
    "priority_domains": ["deep_learning", "computer_vision"],
    "question_strategy": "mix_conceptual_practical",
    "learning_pace": "moderate",
    "profiling_notes": "L'utilisateur semble avoir des bases solides...",
    "recommended_first_topics": ["neural_networks", "backpropagation"]
}
"""


class ProfilerAgent:
    """
    Agent de profilage utilisateur.
    Analyse le profil et prépare la stratégie d'apprentissage.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3  # Faible température pour analyse objective
        )
        self.name = "ProfilerAgent"

    async def analyze(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyser le profil utilisateur et mettre à jour l'état.

        Args:
            state: État actuel du workflow

        Returns:
            Mises à jour à appliquer à l'état
        """
        user_profile = state.get("user_profile", {})
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        # Construire le prompt avec les données utilisateur
        user_context = json.dumps(user_profile, indent=2, ensure_ascii=False)

        messages = [
            SystemMessage(content=PROFILER_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Analyse ce profil utilisateur et propose une stratégie d'apprentissage :

PROFIL UTILISATEUR :
{user_context}

Donne ton analyse en JSON.
            """)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parser la réponse JSON
            # Nettoyer les markdown code blocks si présents
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            analysis = json.loads(response_text)

            # Enregistrer dans le contexte partagé
            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                f"Analyse de profil : Niveau estimé {analysis.get('estimated_level')}/10, Style : {analysis.get('learning_style')}"
            )

            # Enregistrer la décision
            decision = {
                "agent": self.name,
                "timestamp": state.get("updated_at"),
                "decision": "profile_analysis_complete",
                "details": analysis
            }

            # Mettre à jour l'état
            return {
                "user_level": analysis.get("estimated_level", 5),
                "meta_data": {
                    **state.get("meta_data", {}),
                    "profiler_analysis": analysis
                },
                "agent_decisions": state.get("agent_decisions", []) + [decision],
                "current_step": "profiling_complete",
                "next_step": "question_generation"
            }

        except Exception as e:
            error_msg = f"Erreur dans ProfilerAgent: {str(e)}"

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
        """Permet d'utiliser l'agent comme une fonction (requis par LangGraph)"""
        import asyncio
        return asyncio.run(self.analyze(state))


# Instance globale
profiler_agent = ProfilerAgent()

