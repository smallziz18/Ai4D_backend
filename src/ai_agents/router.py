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

@ai_router.post("/chat", response_model=ChatMessageResponse)
async def chat_with_bot(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Converser avec le chatbot IA (mode synchrone).

    Note: cette route est synchrone et peut prendre ~3-5 secondes.
    Pour du streaming temps réel/scalable, vous pouvez aussi utiliser :
    - WebSocket: ws://127.0.0.1:8000/api/ai/v1/realtime/chat/{user_id}
    - Async REST: POST /api/ai/v1/realtime/chat/start
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
            profil = await profile_service.get_profile_by_user_id(current_user.id)
            if profil:
                await profile_service.add_xp(
                    current_user.id,
                    validation_result.get("xp_gained", 200)
                )

                badge = validation_result.get("badge_earned")
                if badge:
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
            profil = await profile_service.get_profile_by_user_id(current_user.id)
            if profil:
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


@ai_router.get("/recommendations/my-roadmap")
async def get_my_personalized_roadmap(
    duration_weeks: int = 12,
    current_user: User = Depends(get_current_user)
):
    """
    Génère automatiquement une roadmap personnalisée basée sur votre profil.

    Cette route analyse votre profil complet (niveau, compétences, objectifs, faiblesses)
    et crée une roadmap sur mesure avec :
    - ✅ Étapes progressives adaptées à votre niveau
    - 📹 Vidéos YouTube recommandées (Machine Learnia, 3Blue1Brown, etc.)
    - 🎓 Cours en ligne gratuits (Coursera, edX, OpenClassrooms)
    - 💻 Projets GitHub pour pratiquer
    - 📊 Critères de validation pour chaque étape

    Args:
        duration_weeks: Durée souhaitée en semaines (4-52)

    Returns:
        Roadmap complète avec toutes les ressources
    """
    try:
        # Récupérer le profil complet
        profil = await profile_service.get_profile_by_user_id(current_user.id)

        if not profil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil non trouvé. Complétez d'abord le questionnaire de profilage."
            )

        # Construire les objectifs à partir du profil
        if profil.objectifs:
            objectives = profil.objectifs
        else:
            # Objectifs par défaut basés sur le niveau
            if profil.niveau <= 3:
                objectives = "Maîtriser les fondamentaux du Machine Learning et faire mes premiers projets"
            elif profil.niveau <= 6:
                objectives = "Approfondir mes connaissances en Deep Learning et réaliser des projets avancés"
            else:
                objectives = "Me spécialiser dans les architectures modernes (Transformers, LLM) et contribuer à la recherche"

        # Extraire les faiblesses pour les prioriser dans la roadmap
        weaknesses_context = ""
        if hasattr(profil, 'analyse_questions_ouvertes') and profil.analyse_questions_ouvertes:
            weaknesses = []

            # Gérer le cas où analyse_questions_ouvertes peut être un dict ou une liste
            analyses = profil.analyse_questions_ouvertes
            if isinstance(analyses, dict):
                analyses = [analyses]
            elif not isinstance(analyses, list):
                analyses = []

            for analysis in analyses:
                # Vérifier que analysis est un dictionnaire
                if isinstance(analysis, dict):
                    score = analysis.get('score_moyen', 10)
                    # S'assurer que score est un nombre
                    try:
                        score = float(score)
                        if score < 6:
                            concept = analysis.get('concept_principal', '')
                            if concept:
                                weaknesses.append(concept)
                    except (TypeError, ValueError):
                        # Ignorer si le score n'est pas convertible
                        continue

            if weaknesses:
                weaknesses_context = f"\n\n⚠️ PRIORITÉS (faiblesses identifiées) : {', '.join(weaknesses[:5])}"
                objectives += weaknesses_context

        # Générer la roadmap personnalisée
        roadmap = await course_recommendation_agent.create_learning_roadmap(
            user_level=profil.niveau,
            user_objectives=objectives,
            user_competences=profil.competences if profil.competences else [],
            duration_weeks=duration_weeks
        )

        # Enrichir avec des infos du profil
        roadmap["profil_utilisateur"] = {
            "niveau": profil.niveau,
            "xp": profil.xp,
            "badges": profil.badges,
            "competences_actuelles": profil.competences,
            "energie_actuelle": profil.energie,
            "objectifs": profil.objectifs
        }

        # Ajouter des statistiques
        roadmap["statistiques"] = {
            "total_ressources": (
                len(roadmap.get("ressources_supplementaires", {}).get("videos_youtube", [])) +
                len(roadmap.get("ressources_supplementaires", {}).get("cours_en_ligne", [])) +
                len(roadmap.get("ressources_supplementaires", {}).get("projets_github", []))
            ),
            "duree_totale_estimee": f"{duration_weeks} semaines",
            "niveau_cible": min(10, profil.niveau + 2),
            "gratuite": True
        }

        return {
            "status": "success",
            "message": f"🎯 Roadmap personnalisée créée pour {duration_weeks} semaines !",
            "roadmap": roadmap
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur génération roadmap: {str(e)}"
        )


@ai_router.post("/chat/generate-roadmap")
async def chat_generate_roadmap_command(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Commande spéciale du chatbot pour générer une roadmap via conversation naturelle.

    L'utilisateur peut dire :
    - "Génère-moi une roadmap"
    - "Je veux un plan d'apprentissage"
    - "Crée mon parcours personnalisé"

    Le chatbot comprend l'intention et génère la roadmap automatiquement.
    """
    try:
        message_lower = request.message.lower()

        # Détecter l'intention de génération de roadmap
        roadmap_keywords = [
            "roadmap", "plan d'apprentissage", "parcours", "feuille de route",
            "programme", "planning", "organisation", "étapes", "progression"
        ]

        is_roadmap_request = any(keyword in message_lower for keyword in roadmap_keywords)

        if not is_roadmap_request:
            # Si ce n'est pas une demande de roadmap, traiter comme un message normal
            return await chat_with_bot(request, current_user)

        # Générer la roadmap automatiquement
        profil = await profile_service.get_profile_by_user_id(current_user.id)

        if not profil:
            return {
                "response": "Pour créer une roadmap personnalisée, je dois d'abord connaître ton profil. Peux-tu compléter le questionnaire de profilage ? 📝",
                "intention": {
                    "primary": "roadmap_request",
                    "confidence": 0.9,
                    "action_required": "complete_profile"
                },
                "conversation_id": f"chat_{current_user.id}",
                "timestamp": datetime.now(UTC).isoformat(),
                "suggestions": [
                    "📝 Compléter le questionnaire",
                    "💬 Poser une question",
                    "📚 Voir les cours disponibles"
                ]
            }

        # Extraire la durée si mentionnée
        duration_weeks = 12  # Par défaut
        import re
        week_match = re.search(r'(\d+)\s*(semaine|week)', message_lower)
        if week_match:
            duration_weeks = min(52, max(4, int(week_match.group(1))))

        # Générer la roadmap
        objectives = profil.objectifs or "Progresser en Machine Learning et Deep Learning"
        roadmap = await course_recommendation_agent.create_learning_roadmap(
            user_level=profil.niveau,
            user_objectives=objectives,
            user_competences=profil.competences or [],
            duration_weeks=duration_weeks
        )

        # Construire une réponse conversationnelle
        response_text = f"""🎯 **Roadmap personnalisée créée !**

J'ai généré un parcours de {duration_weeks} semaines adapté à ton niveau ({profil.niveau}/10).

**📊 Résumé** :
"""

        if "roadmap_suggeree" in roadmap and roadmap["roadmap_suggeree"]:
            response_text += f"\n📍 **{len(roadmap['roadmap_suggeree'])} étapes principales**"
            for i, etape in enumerate(roadmap["roadmap_suggeree"][:3], 1):
                response_text += f"\n  {i}. {etape.get('titre', f'Étape {i}')} ({etape.get('duree_totale', 'durée variable')})"
            if len(roadmap["roadmap_suggeree"]) > 3:
                response_text += f"\n  ... et {len(roadmap['roadmap_suggeree']) - 3} autres étapes"

        if "ressources_supplementaires" in roadmap:
            supp = roadmap["ressources_supplementaires"]
            response_text += f"\n\n**📚 Ressources incluses** :"
            response_text += f"\n  📹 {len(supp.get('videos_youtube', []))} vidéos YouTube"
            response_text += f"\n  🎓 {len(supp.get('cours_en_ligne', []))} cours en ligne gratuits"
            response_text += f"\n  💻 {len(supp.get('projets_github', []))} projets GitHub"

        response_text += "\n\n✅ Toutes les ressources sont **100% gratuites** !"
        response_text += "\n\n👉 Consulte le détail complet dans la section 'roadmap' de la réponse."

        session_id = request.session_id or f"chat_{current_user.id}_{datetime.now(UTC).timestamp()}"

        # Sauvegarder dans l'historique
        await chatbot_service.add_message(
            utilisateur_id=current_user.id,
            session_id=session_id,
            role="user",
            content=request.message
        )

        await chatbot_service.add_message(
            utilisateur_id=current_user.id,
            session_id=session_id,
            role="assistant",
            content=response_text
        )

        return {
            "response": response_text,
            "intention": {
                "primary": "roadmap_generated",
                "confidence": 1.0,
                "duration_weeks": duration_weeks
            },
            "conversation_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "suggestions": [
                "📖 Voir plus de détails",
                "🎯 Modifier la durée",
                "💬 Poser une question"
            ],
            "roadmap": roadmap  # Roadmap complète dans la réponse
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur génération roadmap: {str(e)}"
        )

