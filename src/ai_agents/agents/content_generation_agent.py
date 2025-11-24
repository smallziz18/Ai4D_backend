"""
Agent Générateur de Contenu
- Produit des ressources pédagogiques personnalisées (explications, mini-fiches, exercices).
- Peut appeler un LLM plus tard; pour l'instant génération heuristique.
"""
from typing import Dict, Any

from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service

TEMPLATE_EXPLICATION = """Concept: {concept}\nNiveau cible: {niveau}\nRésumé: {resume}\nExemple simple: {exemple}\nPiège fréquent: {piege}\nQuestion d'auto-vérification: {question}\n"""

class ContentGenerationAgent:
    def __init__(self):
        self.name = "ContentGenerationAgent"

    async def generate(self, state: AgentState) -> Dict[str, Any]:
        niveau = state.get("user_level", 5)
        weaknesses = state.get("weaknesses", []) or ["bases_ml"]
        strengths = state.get("strengths", []) or []

        target_concepts = weaknesses[:3] if niveau < 7 else (weaknesses[:2] + strengths[:2])
        if not target_concepts:
            target_concepts = ["regularisation", "backpropagation"]

        # Génération heuristique
        resources = []
        for c in target_concepts:
            payload = TEMPLATE_EXPLICATION.format(
                concept=c,
                niveau=niveau,
                resume=f"Synthèse adaptée au niveau {niveau} pour le concept {c}.",
                exemple=f"Exemple: Application de {c} dans un mini-modèle.",
                piege="Confusion entre l'objectif et la procédure.",
                question=f"Explique en 2 phrases l'essence de {c}."
            )
            resources.append({
                "concept": c,
                "content_type": "explication",
                "raw": payload,
                "estimated_time_min": 8
            })

        decision = {
            "agent": self.name,
            "decision": "content_generated",
            "details": {"items": len(resources)}
        }

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        await shared_context_service.add_message(user_id, session_id, self.name, f"Contenu pédagogique généré ({len(resources)} items)")

        return {
            "generated_content": resources,
            "agent_decisions": state.get("agent_decisions", []) + [decision],
            "current_step": "content_generation_complete",
            "next_step": "end_or_loop"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.generate(state))

content_generation_agent = ContentGenerationAgent()
