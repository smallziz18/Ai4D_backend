"""
Agent de Progression
- Surveille l'évolution de l'apprenant.
- Détecte précocement stagnation, régression ou sous-estimation de difficulté.
"""
from typing import Dict, Any
from statistics import mean

from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service

class ProgressionAgent:
    def __init__(self):
        self.name = "ProgressionAgent"

    async def monitor(self, state: AgentState) -> Dict[str, Any]:
        history = state.get("agent_decisions", [])
        open_analysis = (state.get("open_question_analysis", {}) or {}).get("questions_analysees", [])
        niveau = state.get("user_level", 5)

        # Indicateurs simples
        avg_open = mean([q.get("score_moyen", 0) for q in open_analysis]) if open_analysis else 0.0
        num_interactions = len(history)

        risk_flags = []
        if avg_open < 3 and niveau > 4:
            risk_flags.append("Niveau surestimé vs performance ouverte")
        if avg_open == 0 and num_interactions > 2:
            risk_flags.append("Absence de réponses ouvertes exploitables")
        if niveau <= 3 and avg_open >= 5:
            risk_flags.append("Potentiel sous-estimé (augmenter challenge)")

        intervention = []
        if "Niveau surestimé vs performance ouverte" in risk_flags:
            intervention.append("Réduire la difficulté des prochains contenus et renforcer explication conceptuelle.")
        if "Absence de réponses ouvertes exploitables" in risk_flags:
            intervention.append("Forcer un set de questions ouvertes obligatoires supervisées.")
        if "Potentiel sous-estimé (augmenter challenge)" in risk_flags:
            intervention.append("Introduire des mini-projets et tâches de raisonnement plus profond.")

        decision = {
            "agent": self.name,
            "decision": "progression_evaluated",
            "details": {
                "avg_open": avg_open,
                "risk_flags": risk_flags,
                "suggested_interventions": intervention
            }
        }

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        await shared_context_service.add_message(user_id, session_id, self.name, f"Progression évaluée (open_avg={avg_open})")

        return {
            "progression_snapshot": {
                "avg_open": avg_open,
                "risk_flags": risk_flags,
                "suggested_interventions": intervention
            },
            "agent_decisions": state.get("agent_decisions", []) + [decision],
            "current_step": "progression_monitored",
            "next_step": "visualization"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.monitor(state))

progression_agent = ProgressionAgent()

