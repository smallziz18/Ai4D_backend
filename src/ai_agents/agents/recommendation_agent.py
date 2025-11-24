"""
Agent de Recommandation
- Curate des ressources externes (articles, vidéos, cours, docs) adaptées au profil évolutif.
- Utilise les forces, faiblesses et le niveau pour pondérer les suggestions.
- Peut intégrer plus tard un fetcher web (YouTube, arXiv, docs officiels) via une couche MCP/outils.
"""
from typing import Dict, Any, List

from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service

# Stub de fetch externe (remplacer plus tard par intégrations réelles)
def _stub_fetch_external_resources(keywords: List[str]) -> List[Dict[str, Any]]:
    base = []
    for kw in keywords:
        base.append({
            "title": f"Guide Fondamental: {kw}",
            "url": f"https://example.com/{kw}",
            "source_type": "article",
            "estimated_time_min": 15,
            "level": "intro",
            "tags": [kw, "theorie"],
            "value_score": 0.62
        })
        base.append({
            "title": f"Video Explicative: {kw}",
            "url": f"https://video.example.com/{kw}",
            "source_type": "video",
            "estimated_time_min": 12,
            "level": "intermediaire",
            "tags": [kw, "visuel"],
            "value_score": 0.74
        })
    return base

class RecommendationAgent:
    def __init__(self):
        self.name = "RecommendationAgent"

    async def recommend(self, state: AgentState) -> Dict[str, Any]:
        user_level = state.get("user_level", 5)
        weaknesses = state.get("weaknesses", []) or []
        strengths = state.get("strengths", []) or []
        profiler_analysis = (state.get("meta_data", {}) or {}).get("profiler_analysis", {})
        learning_style = profiler_analysis.get("learning_style", "mixed")

        # Mots-clés initiaux: faiblesses > forces si niveau < 6
        keywords = []
        if user_level < 6 and weaknesses:
            keywords.extend(weaknesses[:5])
        else:
            keywords.extend(strengths[:3])
        if not keywords:
            keywords = ["bases_machine_learning", "backpropagation"]

        raw_resources = _stub_fetch_external_resources(keywords)

        # Pondération selon style d'apprentissage
        style_weights = {
            "visuel": {"video": 1.2, "article": 0.9, "cours": 1.0},
            "practical": {"video": 1.0, "article": 0.8, "cours": 1.2},
            "theoretical": {"video": 0.85, "article": 1.2, "cours": 1.15},
            "mixed": {"video": 1.0, "article": 1.0, "cours": 1.0}
        }
        sw = style_weights.get(learning_style, style_weights["mixed"])

        curated = []
        for r in raw_resources:
            base_score = r["value_score"]
            w = sw.get(r["source_type"], 1.0)
            # Valorisation si mot-clé correspond à une faiblesse
            weakness_boost = 0.15 if any(wk for wk in weaknesses if wk in r["title"].lower()) else 0.0
            adjusted = min(1.0, base_score * w + weakness_boost)
            difficulty = "facile" if user_level < 4 else ("moyen" if user_level < 7 else "avance")
            curated.append({
                **r,
                "adjusted_score": round(adjusted, 3),
                "difficulty_fit": difficulty
            })

        curated.sort(key=lambda x: x["adjusted_score"], reverse=True)
        top_resources = curated[:8]

        # Recommandations synthétiques
        strategic_notes = []
        if weaknesses:
            strategic_notes.append("Prioriser la remédiation des faiblesses avant d'augmenter la difficulté.")
        if user_level < 4:
            strategic_notes.append("Consolider les fondations avant d'aborder des architectures avancées.")
        if user_level >= 7:
            strategic_notes.append("Introduire progressivement des articles de recherche (Transformers, RL avancé).")

        decision = {
            "agent": self.name,
            "decision": "recommendations_generated",
            "details": {"count": len(top_resources)}
        }

        # Mise à jour conversation
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        await shared_context_service.add_message(
            user_id, session_id, self.name,
            f"Ressources générées: {len(top_resources)} (style={learning_style})"
        )

        return {
            "recommendation_resources": top_resources,
            "strategic_notes": strategic_notes,
            "agent_decisions": state.get("agent_decisions", []) + [decision],
            "current_step": "recommendations_complete",
            "next_step": "planning"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.recommend(state))

recommendation_agent = RecommendationAgent()
