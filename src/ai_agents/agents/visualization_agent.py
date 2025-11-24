"""
Agent de Visualisation
- Produit des résumés analytiques exploitables pour interface.
- Transforme les snapshots en structures prêtes à être rendues (graphes, heatmaps).
"""
from typing import Dict, Any
from datetime import datetime, timezone

from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service

class VisualizationAgent:
    def __init__(self):
        self.name = "VisualizationAgent"

    async def visualize(self, state: AgentState) -> Dict[str, Any]:
        evaluation = (state.get("evaluation_results", {}) or {}).get("evaluation_globale", {})
        progression = state.get("progression_snapshot", {})
        roadmap = state.get("learning_roadmap", {})
        resources = state.get("recommendation_resources", [])

        # Construire une structure simple pour frontend (chart-friendly)
        metrics = {
            "niveau": evaluation.get("niveau_final"),
            "moyenne_open": evaluation.get("moyenne_questions_ouvertes"),
            "score_qcm_vf": evaluation.get("score_qcm_vf"),
            "open_answered": evaluation.get("open_answered"),
            "progression_open_avg": progression.get("avg_open")
        }

        timeline = []
        for phase in (roadmap.get("phases", []) or []):
            timeline.append({
                "phase": phase.get("phase"),
                "title": phase.get("title"),
                "weeks": phase.get("duration_weeks"),
                "focus": phase.get("focus")
            })

        recommended_tags = []
        for r in resources[:5]:
            recommended_tags.extend(r.get("tags", []))
        recommended_tags = list(dict.fromkeys(recommended_tags))

        decision = {
            "agent": self.name,
            "decision": "visualization_built",
            "details": {"metrics_keys": list(metrics.keys())}
        }

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        await shared_context_service.add_message(user_id, session_id, self.name, "Visualisation synthétique générée")

        return {
            "visualization_payload": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
                "roadmap_timeline": timeline,
                "recommended_tags": recommended_tags
            },
            "agent_decisions": state.get("agent_decisions", []) + [decision],
            "current_step": "visualization_complete",
            "next_step": "content_generation"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.visualize(state))

visualization_agent = VisualizationAgent()
