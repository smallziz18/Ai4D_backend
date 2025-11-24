from fastapi import APIRouter, Depends, HTTPException, Body
from src.users.dependencies import get_current_user
from src.users.models import Utilisateur
from src.ai_agents.workflow import (
    analyze_and_create_profile,
    ai_learning_workflow
)
from src.ai_agents.shared_context import shared_context_service
import uuid

router_ai = APIRouter(prefix="/ai/agents", tags=["ai-agents"])

@router_ai.get("/")
async def list_agents():
    return {
        "agents": [
            {"name": "ProfilerAgent", "role": "Analyse du profil"},
            {"name": "QuestionGeneratorAgent", "role": "Génération de questions"},
            {"name": "EvaluatorAgent", "role": "Évaluation des réponses"},
            {"name": "TutoringAgent", "role": "Création du parcours RPG"}
        ],
        "description": "Agents IA multi-agents disponibles"
    }

@router_ai.post("/start")
async def start_agent_session(current_user: Utilisateur = Depends(get_current_user)):
    """Démarrer une nouvelle session multi-agents (profilage)"""
    session_id = str(uuid.uuid4())
    user_profile = {
        "id": str(current_user.id),
        "nom": current_user.nom,
        "prenom": current_user.prenom,
        "username": current_user.username,
        "email": current_user.email,
        "status": current_user.status,
        "niveau_technique": current_user.niveau_technique or 5,
        "competences": current_user.competences or [],
        "objectifs_apprentissage": current_user.objectifs_apprentissage,
        "motivation": current_user.motivation,
        "niveau_energie": current_user.niveau_energie or 5
    }
    # Démarrage profilage + questions
    result = await ai_learning_workflow.start_profiling(str(current_user.id), session_id, user_profile)
    return {
        "session_id": session_id,
        "questions": result.get("questions", []),
        "user_level_estimated": result.get("user_level"),
        "user_level_label_estimated": result.get("user_level_label")
    }

@router_ai.get("/sessions")
async def list_sessions(current_user: Utilisateur = Depends(get_current_user)):
    contexts = shared_context_service.list_contexts(str(current_user.id))
    return {"sessions": contexts}

@router_ai.get("/sessions/{session_id}")
async def get_session_state(session_id: str, current_user: Utilisateur = Depends(get_current_user)):
    state = await ai_learning_workflow.get_workflow_state(str(current_user.id), session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return {"session_id": session_id, "state": state}

@router_ai.delete("/sessions/{session_id}")
async def delete_session(session_id: str, current_user: Utilisateur = Depends(get_current_user)):
    ok = shared_context_service.delete_context(str(current_user.id), session_id)
    return {"deleted": ok, "session_id": session_id}

@router_ai.post("/sessions/{session_id}/responses")
async def submit_session_responses(
    session_id: str,
    responses: list = Body(..., description="Liste des réponses du questionnaire de la session"),
    current_user: Utilisateur = Depends(get_current_user)
):
    result = await analyze_and_create_profile(str(current_user.id), session_id, responses)
    if not result:
        raise HTTPException(status_code=500, detail="Analyse échouée")
    return {
        "session_id": session_id,
        "niveau_final": result.get("user_level"),
        "niveau_label_final": result.get("user_level_label"),
        "evaluation": result.get("evaluation_results"),
        "learning_path": result.get("learning_path"),
        "badges_earned": result.get("badges_earned", []),
        "recommendations": result.get("recommendations", [])
    }

@router_ai.get("/sessions/{session_id}/history")
async def get_conversation_history(session_id: str, current_user: Utilisateur = Depends(get_current_user)):
    ctx = await shared_context_service.get_context(str(current_user.id), session_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Contexte introuvable")
    return {
        "session_id": session_id,
        "conversation_history": ctx.get("conversation_history", [])
    }

@router_ai.post("/sessions/{session_id}/message")
async def add_manual_message(
    session_id: str,
    content: str = Body(..., embed=True),
    current_user: Utilisateur = Depends(get_current_user)
):
    # Permettre au frontend d'ajouter un message utilisateur dans l'historique
    updated = await shared_context_service.add_message(
        str(current_user.id),
        session_id,
        agent="User",
        message=content,
        message_type="user"
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return {"status": "added", "total_interactions": updated.get("total_interactions")}

@router_ai.get("/sessions/{session_id}/summary")
async def get_session_summary(session_id: str, current_user: Utilisateur = Depends(get_current_user)):
    state = await ai_learning_workflow.get_workflow_state(str(current_user.id), session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session introuvable")
    from src.ai_agents.agent_state import get_state_summary
    return {"session_id": session_id, "summary": get_state_summary(state)}
