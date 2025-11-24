"""
Workflow principal LangGraph pour orchestrer les agents multi-agents.
Tous les agents partagent le même contexte (AgentState).
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.ai_agents.agent_state import AgentState, create_initial_state
from src.ai_agents.agents import (
    profiler_agent,
    question_generator_agent,
    evaluator_agent,
    tutoring_agent,
    recommendation_agent,
    planning_agent,
    progression_agent,
    visualization_agent,
    content_generation_agent
)
from src.ai_agents.shared_context import shared_context_service


def should_continue_profiling(state: AgentState) -> Literal["continue", "end"]:
    """Décider si le profilage continue ou se termine"""
    if state.get("error_message"):
        return "end"
    if state.get("current_step") == "profiling_complete":
        return "continue"
    return "end"


def should_generate_questions(state: AgentState) -> Literal["continue", "wait_responses", "end"]:
    """Décider après la génération de questions"""
    if state.get("error_message"):
        return "end"
    if state.get("current_step") == "questions_generated":
        return "wait_responses"
    return "end"


def should_evaluate(state: AgentState) -> Literal["continue", "end"]:
    """Décider si l'évaluation continue"""
    if state.get("error_message"):
        return "end"
    if state.get("current_step") == "responses_received":
        return "continue"
    return "end"


def should_create_tutoring(state: AgentState) -> Literal["continue", "end"]:
    """Décider si on crée le parcours de tutoring"""
    if state.get("error_message"):
        return "end"
    if state.get("current_step") == "evaluation_complete":
        return "continue"
    return "end"


def finalize_workflow(state: AgentState) -> Dict[str, Any]:
    """Finaliser le workflow"""
    return {
        "is_complete": True,
        "current_step": "workflow_complete"
    }


class AILearningWorkflow:
    """
    Workflow LangGraph pour l'apprentissage IA gamifié.
    Orchestration de plusieurs agents spécialisés partageant un contexte commun.
    """

    def __init__(self):
        # Créer le graphe de workflow
        workflow = StateGraph(AgentState)

        # Ajouter les nœuds (agents)
        workflow.add_node("profiler", profiler_agent)
        workflow.add_node("question_generator", question_generator_agent)
        workflow.add_node("evaluator", evaluator_agent)
        workflow.add_node("tutoring", tutoring_agent)
        workflow.add_node("recommendation", recommendation_agent)
        workflow.add_node("planning", planning_agent)
        workflow.add_node("progression", progression_agent)
        workflow.add_node("visualization", visualization_agent)
        workflow.add_node("content_generation", content_generation_agent)
        workflow.add_node("finalize", finalize_workflow)

        # Définir les transitions
        workflow.set_entry_point("profiler")

        # Après profilage → génération de questions
        workflow.add_conditional_edges(
            "profiler",
            should_continue_profiling,
            {
                "continue": "question_generator",
                "end": END
            }
        )

        # Après génération de questions → attendre les réponses (géré par l'API)
        # puis évaluation
        workflow.add_edge("question_generator", END)  # Sort du workflow temporairement

        # Point d'entrée pour l'évaluation (après réception des réponses)
        workflow.add_node("start_evaluation", lambda x: x)  # Noeud passthrough
        workflow.add_edge("start_evaluation", "evaluator")

        # Après évaluation → tutoring
        workflow.add_conditional_edges(
            "evaluator",
            should_create_tutoring,
            {
                "continue": "tutoring",
                "end": END
            }
        )
        # Après tutoring -> recommendation -> planning -> progression -> visualization -> content_generation -> finalize
        workflow.add_edge("tutoring", "recommendation")
        workflow.add_edge("recommendation", "planning")
        workflow.add_edge("planning", "progression")
        workflow.add_edge("progression", "visualization")
        workflow.add_edge("visualization", "content_generation")
        workflow.add_edge("content_generation", "finalize")
        workflow.add_edge("finalize", END)

        # Compiler le graphe avec un checkpointer pour persistence
        self.memory = MemorySaver()
        self.app = workflow.compile(checkpointer=self.memory)

    async def start_profiling(
        self,
        user_id: str,
        session_id: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Démarrer le workflow de profilage.
        Retourne les questions générées.
        """
        # Créer l'état initial
        initial_state = create_initial_state(user_id, session_id, user_profile)

        # Créer ou récupérer le contexte partagé
        await shared_context_service.get_or_create_context(
            user_id,
            session_id,
            initial_data=user_profile
        )

        # Configuration pour le checkpointing
        config = {
            "configurable": {
                "thread_id": f"{user_id}_{session_id}"
            }
        }

        # Exécuter le workflow jusqu'à la génération de questions
        result = await self.app.ainvoke(initial_state, config)

        return {
            "questions": result.get("questions", []),
            "user_level": result.get("user_level"),
            "user_level_label": result.get("user_level_label"),
            "profiler_analysis": result.get("meta_data", {}).get("profiler_analysis"),
            "session_id": session_id
        }

    async def evaluate_responses(
        self,
        user_id: str,
        session_id: str,
        responses: list
    ) -> Dict[str, Any]:
        """
        Évaluer les réponses et créer le parcours d'apprentissage.
        """
        # Récupérer l'état sauvegardé
        config = {
            "configurable": {
                "thread_id": f"{user_id}_{session_id}"
            }
        }

        # Récupérer l'état du checkpoint
        state_snapshot = await self.app.aget_state(config)
        current_state = state_snapshot.values

        # Mettre à jour avec les réponses
        current_state["responses"] = responses
        current_state["current_step"] = "responses_received"

        # Créer un nouveau workflow partant de l'évaluation
        eval_workflow = StateGraph(AgentState)
        eval_workflow.add_node("evaluator", evaluator_agent)
        eval_workflow.add_node("tutoring", tutoring_agent)
        eval_workflow.add_node("recommendation", recommendation_agent)
        eval_workflow.add_node("planning", planning_agent)
        eval_workflow.add_node("progression", progression_agent)
        eval_workflow.add_node("visualization", visualization_agent)
        eval_workflow.add_node("content_generation", content_generation_agent)
        eval_workflow.add_node("finalize", finalize_workflow)

        eval_workflow.set_entry_point("evaluator")
        eval_workflow.add_edge("evaluator", "tutoring")
        eval_workflow.add_edge("tutoring", "recommendation")
        eval_workflow.add_edge("recommendation", "planning")
        eval_workflow.add_edge("planning", "progression")
        eval_workflow.add_edge("progression", "visualization")
        eval_workflow.add_edge("visualization", "content_generation")
        eval_workflow.add_edge("content_generation", "finalize")
        eval_workflow.add_edge("finalize", END)

        eval_app = eval_workflow.compile()

        # Exécuter l'évaluation et le tutoring
        result = await eval_app.ainvoke(current_state)

        return {
            "evaluation_results": result.get("evaluation_results"),
            "user_level": result.get("user_level"),
            "user_level_label": result.get("user_level_label"),
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "recommendations": result.get("recommendation_resources", result.get("recommendations", [])),
            "learning_path": result.get("learning_path"),
            "learning_roadmap": result.get("learning_roadmap"),
            "progression_snapshot": result.get("progression_snapshot"),
            "visualization_payload": result.get("visualization_payload"),
            "generated_content": result.get("generated_content"),
            "tutorials": result.get("tutorials", []),
            "badges_earned": result.get("badges_earned", []),
            "open_question_analysis": result.get("open_question_analysis"),
            "is_complete": result.get("is_complete")
        }

    async def get_workflow_state(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Récupérer l'état actuel du workflow"""
        config = {
            "configurable": {
                "thread_id": f"{user_id}_{session_id}"
            }
        }

        state_snapshot = await self.app.aget_state(config)

        if not state_snapshot:
            return None

        return state_snapshot.values


# Instance globale du workflow
ai_learning_workflow = AILearningWorkflow()


# Fonctions helper pour l'utilisation dans les routes
async def generate_profile_questions(
    user_id: str,
    user_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Générer des questions de profilage pour un utilisateur.
    """
    import uuid
    session_id = str(uuid.uuid4())

    return await ai_learning_workflow.start_profiling(
        user_id,
        session_id,
        user_profile
    )


async def analyze_and_create_profile(
    user_id: str,
    session_id: str,
    responses: list
) -> Dict[str, Any]:
    """
    Analyser les réponses et créer le profil complet.
    """
    return await ai_learning_workflow.evaluate_responses(
        user_id,
        session_id,
        responses
    )
