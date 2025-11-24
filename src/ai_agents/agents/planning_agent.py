"""
Agent de Planification
- Construit des feuilles de route multi-phases dynamiques.
- Ajuste en temps réel selon progression, niveau, énergie et style d'apprentissage.
"""
from typing import Dict, Any
from datetime import datetime, timezone

from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service

class PlanningAgent:
    def __init__(self):
        self.name = "PlanningAgent"

    async def plan(self, state: AgentState) -> Dict[str, Any]:
        user_level = state.get("user_level", 5)
        energy = state.get("user_profile", {}).get("niveau_energie", 5)
        learning_style = (state.get("meta_data", {}) or {}).get("profiler_analysis", {}).get("learning_style", "mixed")
        weaknesses = state.get("weaknesses", []) or []
        strengths = state.get("strengths", []) or []

        phases = []
        # Phase 1: Stabilisation / Fondations
        phases.append({
            "phase": 1,
            "title": "Consolidation des Fondations",
            "duration_weeks": 2 if user_level < 6 else 1,
            "focus": weaknesses[:3] if weaknesses else ["notions_de_base"],
            "style_modulation": learning_style,
            "suggested_daily_minutes": 45 if energy >= 6 else 30,
            "outcomes": ["Compréhension stable des concepts clés", "Vocabulaire technique correct"],
            "milestones": ["Quiz de validation fondations", "Mini-projet guided"]
        })
        # Phase 2: Expansion
        phases.append({
            "phase": 2,
            "title": "Expansion Conceptuelle",
            "duration_weeks": 3,
            "focus": strengths[:3] + ["approfondissement_architectures"],
            "style_modulation": learning_style,
            "suggested_daily_minutes": 60 if energy >= 5 else 40,
            "outcomes": ["Capacité à expliquer architectures principales", "Transition vers raisonnement autonome"],
            "milestones": ["Rédaction d'une synthèse technique", "Pair-review d'explications"]
        })
        # Phase 3: Intégration / Projets
        phases.append({
            "phase": 3,
            "title": "Intégration par Projets",
            "duration_weeks": 4,
            "focus": ["projet_applique", "optimisation", "erreurs_et_debug"],
            "style_modulation": learning_style,
            "suggested_daily_minutes": 75 if energy >= 7 else 50,
            "outcomes": ["Capacité à structurer un pipeline ML", "Compréhension des compromis"],
            "milestones": ["Projet intégrateur", "Revue de code approfondie"]
        })
        # Phase 4: Spécialisation avancée
        phases.append({
            "phase": 4,
            "title": "Spécialisation Avancée",
            "duration_weeks": 4 if user_level >= 7 else 3,
            "focus": ["transformers", "fine_tuning", "evaluation_avancee"],
            "style_modulation": learning_style,
            "suggested_daily_minutes": 90 if energy >= 8 else 60,
            "outcomes": ["Maîtrise des architectures modernes", "Capacité à comparer modèles"],
            "milestones": ["Analyse critique d'article", "Benchmark comparatif"]
        })

        roadmap = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "adaptive": True,
            "phases": phases,
            "total_duration_weeks": sum(p["duration_weeks"] for p in phases)
        }

        decision = {
            "agent": self.name,
            "decision": "roadmap_generated",
            "details": {"phases": len(phases)}
        }

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        await shared_context_service.add_message(user_id, session_id, self.name, f"Feuille de route générée ({len(phases)} phases)")

        return {
            "learning_roadmap": roadmap,
            "agent_decisions": state.get("agent_decisions", []) + [decision],
            "current_step": "planning_complete",
            "next_step": "progression_monitoring"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.plan(state))

planning_agent = PlanningAgent()
