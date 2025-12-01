"""
Routes API pour les agents IA (chatbot, cours, progression, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, UTC

from src.users.dependencies import get_current_user
from src.users.models import Utilisateur as User
from src.ai_agents.agents.chatbot_agent import chatbot_agent
from src.ai_agents.agents.course_manager_agent import course_manager_agent
from src.ai_agents.agents.tutoring_agent import tutoring_agent
from src.ai_agents.agents.course_recommendation_agent import course_recommendation_agent
from src.profile.learning_services import (
    course_service,
    progression_service,
    chatbot_service,
    learning_path_service
)
from src.profile.services import profile_service
from src.celery_tasks import app as celery_app


# Schémas Pydantic
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    response: str
    intention: Dict[str, Any]
    conversation_id: str
    timestamp: str
    suggestions: List[str]


class CourseRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    duration_weeks: int = Field(default=6, ge=2, le=16)


class ModuleCompletionRequest(BaseModel):
    module_id: str
    evaluation_score: float = Field(..., ge=0, le=100)
    time_spent_minutes: int = Field(..., ge=0)


class LessonCompletionRequest(BaseModel):
    lesson_id: str
    time_spent_minutes: int = Field(..., ge=0)


class AgentTaskStartRequest(BaseModel):
    agent_type: str = Field(..., description="Type d'agent: chatbot, course, module")
    params: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        # Permettre d'autres types de données
        json_schema_extra = {
            "example": {
                "agent_type": "chatbot",
                "params": {
                    "message": "Hello"
                }
            }
        }


# Router
ai_router = APIRouter(tags=["AI Agents"])


# ==================== AGENTS ASYNC (CELERY) ====================

@ai_router.post("/agents/start")
async def start_agent_task(
    request: AgentTaskStartRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Démarrer une tâche d'agent IA de manière asynchrone avec Celery.

    Exemple:
    {
        "agent_type": "chatbot",
        "params": {"message": "Hello"}
    }
    """
    try:
        agent_type = request.agent_type.lower().strip()
        params = request.params or {}

        if agent_type == "chatbot":
            # Tâche chatbot
            message = params.get("message", "")
            if not message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le paramètre 'message' est requis pour chatbot"
                )

            session_id = params.get("session_id", f"chat_{current_user.id}_{datetime.now().timestamp()}")

            # Récupérer le profil pour le contexte
            profil = await profile_service.get_profile_by_user_id(current_user.id)
            user_context = {
                "niveau_technique": profil.niveau if profil else 5,
                "competences": profil.competences if profil else [],
                "objectifs": profil.objectifs if profil else "",
            } if profil else None

            task = celery_app.send_task(
                'chatbot_task',
                args=[str(current_user.id), session_id, message, user_context]
            )

            return {
                "status": "queued",
                "task_id": task.id,
                "agent_type": "chatbot",
                "message": "Chatbot task démarrée"
            }

        elif agent_type == "course":
            # Tâche génération de cours
            topic = params.get("topic", "")
            if not topic:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le paramètre 'topic' est requis pour course"
                )

            duration_weeks = int(params.get("duration_weeks", 6))

            profil = await profile_service.get_profile_by_user_id(current_user.id)
            user_level = profil.niveau if profil else 5

            task = celery_app.send_task(
                'course_generation_task',
                args=[str(current_user.id), topic, user_level, duration_weeks]
            )

            return {
                "status": "queued",
                "task_id": task.id,
                "agent_type": "course",
                "message": "Course generation task démarrée"
            }

        elif agent_type == "module":
            # Tâche complétion de module
            course_id = params.get("course_id", "")
            module_id = params.get("module_id", "")
            score = float(params.get("score", 0.0))
            time_spent = int(params.get("time_spent_minutes", 0))

            if not course_id or not module_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Les paramètres 'course_id' et 'module_id' sont requis"
                )

            task = celery_app.send_task(
                'module_completion_task',
                args=[str(current_user.id), course_id, module_id, score, time_spent]
            )

            return {
                "status": "queued",
                "task_id": task.id,
                "agent_type": "module",
                "message": "Module completion task démarrée"
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent type '{agent_type}' non supporté. Utilisez: chatbot, course, module"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur start_agent_task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur démarrage agent: {str(e)}"
        )


@ai_router.get("/agents/status/{task_id}")
async def get_agent_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer le statut d'une tâche agent.
    """
    try:
        task = celery_app.AsyncResult(task_id)

        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.status == "SUCCESS" else None,
            "error": str(task.info) if task.status == "FAILURE" else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération statut: {str(e)}"
        )


# ==================== CHATBOT ====================

@ai_router.post("/chat", response_model=ChatMessageResponse, deprecated=True)
async def chat_with_bot(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    ⚠️ DEPRECATED - Utilisez WebSocket /api/ai/v1/realtime/chat/{user_id} pour streaming temps réel

    Converser avec le chatbot IA (version synchrone - NON SCALABLE).

    Cette route bloque le serveur pendant 3-5 secondes.
    Pour une architecture scalable avec streaming, utilisez :
    - WebSocket: ws://127.0.0.1:8000/api/ai/v1/realtime/chat/{user_id}
    - Async REST: POST /api/ai/v1/realtime/chat/start

    Voir WEBSOCKET_IMPLEMENTATION.md pour les détails.
    """
    try:
        # Récupérer le profil utilisateur pour le contexte
        profil = await profile_service.get_profile_by_user_id(current_user.id)

        user_context = None
        if profil:
            user_context = {
                "niveau_technique": profil.niveau,
                "competences": profil.competences,
                "objectifs": profil.objectifs,
                "xp": profil.xp,
                "badges": profil.badges
            }

        # Générer un session_id si non fourni
        session_id = request.session_id or f"chat_{current_user.id}_{datetime.now(UTC).timestamp()}"

        # Appeler le chatbot
        response = await chatbot_agent.chat(
            user_id=str(current_user.id),
            session_id=session_id,
            message=request.message,
            user_context=user_context
        )

        # Sauvegarder dans MongoDB
        await chatbot_service.add_message(
            utilisateur_id=current_user.id,
            session_id=session_id,
            role="user",
            content=request.message,
            intention=response.get("intention")
        )

        await chatbot_service.add_message(
            utilisateur_id=current_user.id,
            session_id=session_id,
            role="assistant",
            content=response["response"]
        )

        return ChatMessageResponse(**response)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur chatbot: {str(e)}"
        )


@ai_router.get("/chat/history")
async def get_chat_history(
    session_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer l'historique de conversation.
    """
    try:
        if session_id:
            conversation = await chatbot_service.get_conversation(
                utilisateur_id=current_user.id,
                session_id=session_id
            )
            return {
                "conversation": conversation.model_dump() if conversation else None
            }
        else:
            conversations = await chatbot_service.get_recent_conversations(
                utilisateur_id=current_user.id,
                limit=limit
            )
            return {
                "conversations": [conv.model_dump() for conv in conversations]
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération historique: {str(e)}"
        )


# ==================== COURS ====================

@ai_router.post("/courses/generate")
async def generate_course_roadmap(
    request: CourseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Générer une roadmap de cours personnalisée.
    """
    try:
        # Récupérer le profil pour adapter au niveau
        profil = await profile_service.get_profile_by_user_id(current_user.id)
        user_level = profil.niveau if profil else 5
        user_objectives = profil.objectifs if profil else "Apprendre l'IA"

        # Générer la roadmap
        roadmap = await course_manager_agent.create_course_roadmap(
            course_topic=request.topic,
            user_level=user_level,
            user_objectives=user_objectives,
            duration_weeks=request.duration_weeks
        )

        # Sauvegarder le cours dans MongoDB
        course_id = await course_service.create_course(roadmap)

        # Créer la progression pour l'utilisateur
        await progression_service.create_progression(
            utilisateur_id=current_user.id,
            course_id=roadmap["cours"]["id"]
        )

        # Incrémenter les inscriptions
        await course_service.increment_enrollment(roadmap["cours"]["id"])

        return {
            "message": "Roadmap générée avec succès",
            "course_id": course_id,
            "roadmap": roadmap
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur génération roadmap: {str(e)}"
        )


@ai_router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer un cours complet.
    """
    try:
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cours non trouvé"
            )

        # Récupérer la progression
        progression = await progression_service.get_progression(
            utilisateur_id=current_user.id,
            course_id=course_id
        )

        return {
            "course": course.model_dump(),
            "progression": progression.model_dump() if progression else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération cours: {str(e)}"
        )


@ai_router.get("/courses")
async def search_courses(
    tags: Optional[str] = None,
    niveau: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Rechercher des cours.
    """
    try:
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
            courses = await course_service.search_courses(tags_list, niveau)
        elif niveau:
            courses = await course_service.get_courses_by_level(niveau)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fournir au moins tags ou niveau"
            )

        return {
            "courses": [course.model_dump() for course in courses]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur recherche cours: {str(e)}"
        )


# ==================== PROGRESSION ====================

@ai_router.get("/progression")
async def get_all_progressions(
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer toutes les progressions de l'utilisateur.
    """
    try:
        progressions = await progression_service.get_all_progressions(current_user.id)
        return {
            "progressions": [prog.model_dump() for prog in progressions]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération progressions: {str(e)}"
        )


@ai_router.post("/progression/{course_id}/module/complete")
async def complete_module(
    course_id: str,
    request: ModuleCompletionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Marquer un module comme complété et lancer l'évaluation.
    """
    try:
        # Valider la complétion du module
        validation_result = await course_manager_agent.validate_module_completion(
            user_id=str(current_user.id),
            session_id=f"course_{course_id}",
            module_id=request.module_id,
            evaluation_results={
                "score": request.evaluation_score,
                "seuil_reussite": 70
            }
        )

        # Si validé, marquer comme complété
        if validation_result.get("module_completed"):
            await progression_service.complete_module(
                utilisateur_id=current_user.id,
                course_id=course_id,
                module_id=request.module_id,
                evaluation_result={
                    "score": request.evaluation_score,
                    "passed": True,
                    "date": datetime.now(UTC).isoformat()
                }
            )

            # Ajouter du temps
            await progression_service.add_time_spent(
                utilisateur_id=current_user.id,
                course_id=course_id,
                minutes=request.time_spent_minutes,
                module_id=request.module_id
            )

            # Gagner XP et badge
            if profil := await profile_service.get_profile_by_user_id(current_user.id):
                await profile_service.add_xp(
                    current_user.id,
                    validation_result.get("xp_gained", 200)
                )

                if badge := validation_result.get("badge_earned"):
                    await profile_service.add_badge(current_user.id, badge)

        return validation_result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur complétion module: {str(e)}"
        )


@ai_router.post("/progression/{course_id}/lesson/complete")
async def complete_lesson(
    course_id: str,
    request: LessonCompletionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Marquer une leçon comme complétée.
    """
    try:
        success = await progression_service.complete_lesson(
            utilisateur_id=current_user.id,
            course_id=course_id,
            lesson_id=request.lesson_id
        )

        if success:
            await progression_service.add_time_spent(
                utilisateur_id=current_user.id,
                course_id=course_id,
                minutes=request.time_spent_minutes
            )

            # Gagner un peu d'XP
            if profil := await profile_service.get_profile_by_user_id(current_user.id):
                await profile_service.add_xp(current_user.id, 10)

        return {
            "success": success,
            "message": "Leçon complétée" if success else "Erreur"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur complétion leçon: {str(e)}"
        )


# ==================== LEARNING PATH ====================

@ai_router.get("/learning-path")
async def get_learning_path(
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer le parcours d'apprentissage personnalisé.
    """
    try:
        learning_path = await learning_path_service.get_learning_path(current_user.id)

        if not learning_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parcours non trouvé. Complétez d'abord le questionnaire de profilage."
            )

        return {
            "learning_path": learning_path.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération parcours: {str(e)}"
        )


@ai_router.post("/learning-path/quest/{quest_id}/complete")
async def complete_quest(
    quest_id: str,
    xp_earned: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Marquer une quête comme complétée.
    """
    try:
        success = await learning_path_service.complete_quest(
            utilisateur_id=current_user.id,
            quest_id=quest_id,
            xp_earned=xp_earned
        )

        if success:
            # Mettre à jour le profil
            await profile_service.add_xp(current_user.id, xp_earned)

        return {
            "success": success,
            "xp_earned": xp_earned,
            "message": "Quête complétée ! 🎉"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur complétion quête: {str(e)}"
        )


# ==================== RESSOURCES ====================

@ai_router.get("/resources/recommend")
async def recommend_resources(
    topic: str,
    resource_type: str = "all",
    current_user: User = Depends(get_current_user)
):
    """
    Recommander des ressources pour un sujet.
    """
    try:
        profil = await profile_service.get_profile_by_user_id(current_user.id)
        user_level = profil.niveau if profil else 5

        resources = await course_manager_agent.recommend_resources(
            topic=topic,
            user_level=user_level,
            resource_type=resource_type
        )

        return {
            "topic": topic,
            "user_level": user_level,
            "resources": resources
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur recommandation ressources: {str(e)}"
        )


# ==================== TUTORING (NOUVEAU) ====================


class ExplainConceptRequest(BaseModel):
    concept: str = Field(..., min_length=3, max_length=200, description="Concept à expliquer")


@ai_router.post("/tutoring/explain")
async def explain_concept(
    request: ExplainConceptRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Explique un concept de manière adaptée au niveau de l'utilisateur.

    Le tuteur IA fournit :
    - Explication pédagogique
    - Analogie concrète
    - Exemples de code
    - Exercices pratiques
    - Ressources complémentaires
    """
    try:
        profil = await profile_service.get_profile_by_user_id(current_user.id)

        user_context = {}
        if profil:
            user_context = {
                "competences": profil.competences,
                "objectifs": profil.objectifs,
                "niveau": profil.niveau
            }

        user_level = profil.niveau if profil else 5

        # Obtenir l'explication du tuteur
        explanation = await tutoring_agent.explain_concept(
            concept=request.concept,
            user_level=user_level,
            user_context=user_context
        )

        return {
            "status": "success",
            "concept": request.concept,
            "explication": explanation
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur explication concept: {str(e)}"
        )


class ExerciseRequest(BaseModel):
    topic: str = Field(..., description="Sujet des exercices")
    difficulty: str = Field(default="moyen", description="facile|moyen|difficile")


@ai_router.post("/tutoring/exercises")
async def suggest_exercises(
    request: ExerciseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Suggère des exercices pratiques adaptés au niveau.
    """
    try:
        profil = await profile_service.get_profile_by_user_id(current_user.id)
        user_level = profil.niveau if profil else 5

        exercises = await tutoring_agent.suggest_exercises(
            topic=request.topic,
            difficulty=request.difficulty,
            user_level=user_level
        )

        return {
            "status": "success",
            "topic": request.topic,
            "difficulty": request.difficulty,
            "exercices": exercises
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur suggestion exercices: {str(e)}"
        )


@ai_router.get("/tutoring/difficulties")
async def detect_difficulties(
    session_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Détecte les difficultés d'apprentissage de l'utilisateur.

    Analyse l'historique pour identifier :
    - Sujets récurrents (= difficultés potentielles)
    - Signaux de confusion
    - Recommandations pour débloquer
    """
    try:
        session_id = session_id or f"default_{current_user.id}"

        difficulties = await tutoring_agent.detect_difficulties(
            user_id=str(current_user.id),
            session_id=session_id
        )

        return {
            "status": "success",
            "analyse": difficulties
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur détection difficultés: {str(e)}"
        )


# ==================== COURSE RECOMMENDATIONS (NOUVEAU) ====================


@ai_router.get("/recommendations/youtube")
async def search_youtube_resources(
    topic: str,
    language: str = "fr",
    max_results: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Recherche des vidéos YouTube éducatives sur un sujet.

    Retourne des vidéos de qualité (3Blue1Brown, Machine Learnia, etc.)
    """
    try:
        videos = await course_recommendation_agent.search_youtube_videos(
            topic=topic,
            language=language,
            max_results=max_results
        )

        return {
            "status": "success",
            "topic": topic,
            "language": language,
            "videos": videos
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur recherche YouTube: {str(e)}"
        )


@ai_router.get("/recommendations/courses")
async def search_online_courses(
    topic: str,
    free_only: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    Recherche des cours en ligne (Coursera, edX, OpenClassrooms, etc.).

    Priorité aux cours gratuits si free_only=True.
    """
    try:
        courses = await course_recommendation_agent.search_online_courses(
            topic=topic,
            free_only=free_only
        )

        return {
            "status": "success",
            "topic": topic,
            "free_only": free_only,
            "cours": courses
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur recherche cours: {str(e)}"
        )


@ai_router.get("/recommendations/projects")
async def search_github_projects(
    topic: str,
    difficulty: str = "beginner",
    current_user: User = Depends(get_current_user)
):
    """
    Recherche des projets GitHub éducatifs.

    Difficulté: beginner | intermediate | advanced
    """
    try:
        projects = await course_recommendation_agent.search_github_projects(
            topic=topic,
            difficulty=difficulty
        )

        return {
            "status": "success",
            "topic": topic,
            "difficulty": difficulty,
            "projets": projects
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur recherche projets: {str(e)}"
        )


class RoadmapRequest(BaseModel):
    objectives: str = Field(..., min_length=10, description="Objectifs d'apprentissage")
    duration_weeks: int = Field(default=12, ge=4, le=52, description="Durée en semaines")


@ai_router.post("/recommendations/roadmap")
async def create_learning_roadmap(
    request: RoadmapRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Crée une roadmap d'apprentissage personnalisée avec ressources gratuites.

    La roadmap inclut :
    - Étapes progressives semaine par semaine
    - Ressources gratuites (YouTube, Coursera, GitHub)
    - Mini-projets pratiques
    - Critères de validation
    """
    try:
        profil = await profile_service.get_profile_by_user_id(current_user.id)

        user_level = profil.niveau if profil else 5
        user_competences = profil.competences if profil else []

        roadmap = await course_recommendation_agent.create_learning_roadmap(
            user_level=user_level,
            user_objectives=request.objectives,
            user_competences=user_competences,
            duration_weeks=request.duration_weeks
        )

        return {
            "status": "success",
            "roadmap": roadmap,
            "user_level": user_level,
            "duration_weeks": request.duration_weeks
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur création roadmap: {str(e)}"
        )

