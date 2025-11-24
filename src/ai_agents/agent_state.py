"""
État partagé entre les agents dans le workflow LangGraph.
TypedDict pour typage fort et validation.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime, timezone
import operator


class AgentState(TypedDict):
    """
    État partagé entre tous les agents dans le workflow LangGraph.

    Chaque agent peut lire et modifier cet état.
    Les modifications sont mergées automatiquement par LangGraph.
    """

    # Identifiants
    user_id: str
    session_id: str

    # État du workflow
    current_step: str  # profiling, question_generation, evaluation, tutoring, visualization
    next_step: Optional[str]

    # Données utilisateur
    user_profile: Optional[Dict[str, Any]]
    user_level: int  # Niveau estimé 1-10
    user_level_label: str  # Label lisible du niveau
    user_competences: List[str]
    user_objectifs: Optional[str]

    # Questions et réponses
    questions: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    current_question_index: int

    # Analyse et évaluation
    evaluation_results: Optional[Dict[str, Any]]
    open_question_analysis: Optional[Dict[str, Any]]  # Analyse des questions ouvertes
    strengths: List[str]  # Forces identifiées
    weaknesses: List[str]  # Faiblesses identifiées

    # Recommandations et tutoriels
    recommendations: List[str]
    tutorials: List[Dict[str, Any]]
    learning_path: Optional[Dict[str, Any]]  # Parcours d'apprentissage personnalisé

    # Gamification
    xp_earned: int
    badges_earned: List[str]
    achievements: List[Dict[str, Any]]

    # Historique et contexte
    conversation_history: Annotated[List[Dict[str, Any]], operator.add]  # Merge par addition
    agent_decisions: List[Dict[str, Any]]  # Décisions prises par chaque agent

    # Métadonnées
    created_at: str
    updated_at: str
    meta_data: Dict[str, Any]

    # Flags et contrôle
    is_complete: bool
    needs_human_review: bool
    error_message: Optional[str]

    # Nouvelles clés pour nouveaux agents
    learning_roadmap: Optional[Dict[str, Any]]  # Feuille de route multi-phases
    progression_snapshot: Optional[Dict[str, Any]]  # Indicateurs progression
    visualization_payload: Optional[Dict[str, Any]]  # Données pour frontend
    generated_content: List[Dict[str, Any]]  # Contenu pédagogique généré
    recommendation_resources: List[Dict[str, Any]]  # Ressources recommandées détaillées


def create_initial_state(
    user_id: str,
    session_id: str,
    user_profile: Optional[Dict[str, Any]] = None
) -> AgentState:
    """Créer l'état initial pour un nouveau workflow"""
    now = datetime.now(timezone.utc).isoformat()

    return AgentState(
        user_id=user_id,
        session_id=session_id,
        current_step="profiling",
        next_step="question_generation",
        user_profile=user_profile or {},
        user_level=5,  # Niveau par défaut
        user_competences=[],
        user_objectifs=None,
        questions=[],
        responses=[],
        current_question_index=0,
        evaluation_results=None,
        open_question_analysis=None,
        strengths=[],
        weaknesses=[],
        recommendations=[],
        tutorials=[],
        learning_path=None,
        xp_earned=0,
        badges_earned=[],
        achievements=[],
        conversation_history=[],
        agent_decisions=[],
        created_at=now,
        updated_at=now,
        meta_data={},
        is_complete=False,
        needs_human_review=False,
        error_message=None,
        user_level_label="Indéterminé",
        learning_roadmap=None,
        progression_snapshot=None,
        visualization_payload=None,
        generated_content=[],
        recommendation_resources=[]
    )


def get_state_summary(state: AgentState) -> Dict[str, Any]:
    """Obtenir un résumé de l'état pour logging/debugging"""
    return {
        "user_id": state["user_id"],
        "session_id": state["session_id"],
        "current_step": state["current_step"],
        "next_step": state["next_step"],
        "user_level": state["user_level"],
        "num_questions": len(state["questions"]),
        "num_responses": len(state["responses"]),
        "num_recommendations": len(state["recommendations"]),
        "xp_earned": state["xp_earned"],
        "badges_earned": state["badges_earned"],
        "is_complete": state["is_complete"],
        "needs_human_review": state["needs_human_review"]
    }
