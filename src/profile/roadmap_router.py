"""
Routes API pour la gestion des roadmaps et progression utilisateur.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field

from src.users.dependencies import get_current_user
from src.users.schema import UtilisateurRead
from src.profile.roadmap_services import roadmap_service
from src.profile.services import ProfileService

# Router
roadmap_router = APIRouter(prefix="/roadmap", tags=["Roadmap & Progression"])

# Service
profile_service = ProfileService()


# Schémas Pydantic
class RoadmapGenerateRequest(BaseModel):
    duration_weeks: int = Field(default=12, ge=4, le=52, description="Durée en semaines")
    force_regenerate: bool = Field(default=False, description="Forcer la régénération")


class LessonCompleteRequest(BaseModel):
    lesson_id: str
    time_spent_minutes: int = Field(default=0, ge=0)


class ModuleCompleteRequest(BaseModel):
    module_id: str
    evaluation_score: float = Field(ge=0, le=100)


class ModuleProgressRequest(BaseModel):
    module_id: str
    lesson_id: Optional[str] = None
    time_spent_minutes: int = Field(default=0, ge=0)


class UserNoteRequest(BaseModel):
    module_id: str
    content: str


class ProjectSubmitRequest(BaseModel):
    module_id: str
    title: str
    description: str
    github_url: Optional[str] = None
    demo_url: Optional[str] = None


# Routes
@roadmap_router.post("/generate", summary="🎯 Générer ma roadmap personnalisée")
async def generate_my_roadmap(
    request: RoadmapGenerateRequest = Body(...),
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Génère une roadmap personnalisée basée sur votre profil complet.

    La roadmap inclut :
    - 📚 Modules progressifs adaptés à votre niveau
    - 🎥 Ressources YouTube (Machine Learnia, 3Blue1Brown, etc.)
    - 🎓 Cours en ligne gratuits (Coursera, OpenClassrooms, etc.)
    - 💻 Projets GitHub pour pratiquer
    - 📊 Évaluations pour valider vos compétences
    - 🏆 Système XP et badges

    Args:
        duration_weeks: Durée souhaitée (4-52 semaines)
        force_regenerate: Forcer la création d'une nouvelle roadmap

    Returns:
        Roadmap complète avec tracking de progression
    """
    try:
        # Récupérer le profil
        profil = await profile_service.get_profile_by_user_id(current_user.id)

        if not profil:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil non trouvé. Complétez d'abord le questionnaire de profilage."
            )

        # Générer et sauvegarder la roadmap
        roadmap = await roadmap_service.create_and_save_roadmap(
            user_id=current_user.id,
            profil=profil,
            duration_weeks=request.duration_weeks,
            force_regenerate=request.force_regenerate
        )

        return {
            "status": "success",
            "message": f"🎯 Roadmap créée pour {request.duration_weeks} semaines !",
            "roadmap": roadmap
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur génération roadmap: {str(e)}"
        )


@roadmap_router.get("/my-active", summary="📖 Ma roadmap active")
async def get_my_active_roadmap(
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Récupère votre roadmap active avec votre progression actuelle.

    Returns:
        - Roadmap complète
        - Progression en %
        - Module actuel
        - XP gagné
        - Temps passé
    """
    try:
        roadmap = await roadmap_service.get_active_roadmap(current_user.id)

        if not roadmap:
            return {
                "status": "no_active_roadmap",
                "message": "Aucune roadmap active. Générez-en une avec POST /roadmap/generate",
                "roadmap": None
            }

        return {
            "status": "success",
            "roadmap": roadmap
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération roadmap: {str(e)}"
        )


@roadmap_router.get("/progression/{course_id}", summary="📊 Ma progression détaillée")
async def get_my_progression(
    course_id: str,
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Récupère votre progression détaillée pour un cours spécifique.

    Args:
        course_id: ID du cours

    Returns:
        Progression complète avec modules, leçons, évaluations, projets
    """
    try:
        progression = await roadmap_service.get_user_progression(
            user_id=current_user.id,
            course_id=course_id
        )

        if not progression:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progression non trouvée pour ce cours"
            )

        return {
            "status": "success",
            "progression": progression
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération progression: {str(e)}"
        )


@roadmap_router.post("/progress/module", summary="⏱️ Mettre à jour progression module")
async def update_module_progress(
    request: ModuleProgressRequest = Body(...),
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Met à jour votre progression dans un module.

    Utilisez cette route pendant que vous étudiez un module pour :
    - Suivre le temps passé
    - Sauvegarder votre position actuelle
    - Mettre à jour le module/leçon en cours

    Args:
        module_id: ID du module
        lesson_id: ID de la leçon (optionnel)
        time_spent_minutes: Temps passé en minutes
    """
    try:
        # Récupérer la roadmap active pour obtenir le course_id
        roadmap = await roadmap_service.get_active_roadmap(current_user.id)

        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune roadmap active trouvée"
            )

        course_id = roadmap.get("course_id")

        result = await roadmap_service.update_module_progress(
            user_id=current_user.id,
            course_id=course_id,
            module_id=request.module_id,
            lesson_id=request.lesson_id,
            time_spent_minutes=request.time_spent_minutes
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur mise à jour progression: {str(e)}"
        )


@roadmap_router.post("/complete/lesson", summary="✅ Compléter une leçon")
async def complete_lesson(
    request: LessonCompleteRequest = Body(...),
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Marque une leçon comme complétée et gagne de l'XP.

    Args:
        lesson_id: ID de la leçon complétée
        time_spent_minutes: Temps passé sur la leçon

    Returns:
        - Confirmation
        - XP gagné
        - Prochaine leçon suggérée
    """
    try:
        roadmap = await roadmap_service.get_active_roadmap(current_user.id)

        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune roadmap active"
            )

        course_id = roadmap.get("course_id")

        result = await roadmap_service.complete_lesson(
            user_id=current_user.id,
            course_id=course_id,
            lesson_id=request.lesson_id,
            xp_earned=10
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur complétion leçon: {str(e)}"
        )


@roadmap_router.post("/complete/module", summary="🎯 Compléter un module")
async def complete_module(
    request: ModuleCompleteRequest = Body(...),
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Marque un module comme complété après validation de l'évaluation.

    L'évaluation doit avoir un score >= 70% pour valider le module.

    Args:
        module_id: ID du module
        evaluation_score: Score de l'évaluation (0-100)

    Returns:
        - Validation du module
        - XP gagné
        - Module suivant débloqué
        - Badge potentiel
    """
    try:
        roadmap = await roadmap_service.get_active_roadmap(current_user.id)

        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune roadmap active"
            )

        course_id = roadmap.get("course_id")

        result = await roadmap_service.complete_module(
            user_id=current_user.id,
            course_id=course_id,
            module_id=request.module_id,
            evaluation_score=request.evaluation_score,
            xp_earned=50
        )

        # Synchroniser l'XP avec le profil global
        if result.get("passed"):
            profil = await profile_service.get_profile_by_user_id(current_user.id)
            if profil:
                await profile_service.add_xp(
                    user_id=current_user.id,
                    xp_amount=result.get("xp_earned", 0),
                    reason=f"Module complété: {request.module_id}"
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur complétion module: {str(e)}"
        )


@roadmap_router.post("/notes/add", summary="📝 Ajouter une note")
async def add_note(
    request: UserNoteRequest = Body(...),
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Ajoute une note personnelle sur un module.

    Utile pour :
    - Prendre des notes pendant l'apprentissage
    - Marquer des concepts importants
    - Sauvegarder des réflexions
    """
    try:
        roadmap = await roadmap_service.get_active_roadmap(current_user.id)

        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune roadmap active"
            )

        course_id = roadmap.get("course_id")

        result = await roadmap_service.add_user_note(
            user_id=current_user.id,
            course_id=course_id,
            module_id=request.module_id,
            note_content=request.content
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur ajout note: {str(e)}"
        )


@roadmap_router.post("/projects/submit", summary="🚀 Soumettre un projet")
async def submit_project(
    request: ProjectSubmitRequest = Body(...),
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Soumet un projet de module complété.

    Les projets valident votre maîtrise pratique et rapportent un bonus d'XP.

    Args:
        module_id: ID du module
        title: Titre du projet
        description: Description du projet
        github_url: URL du repository GitHub (optionnel)
        demo_url: URL de la démo (optionnel)

    Returns:
        - Confirmation
        - +100 XP bonus
    """
    try:
        roadmap = await roadmap_service.get_active_roadmap(current_user.id)

        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune roadmap active"
            )

        course_id = roadmap.get("course_id")

        project_data = {
            "title": request.title,
            "description": request.description,
            "github_url": request.github_url,
            "demo_url": request.demo_url
        }

        result = await roadmap_service.submit_project(
            user_id=current_user.id,
            course_id=course_id,
            module_id=request.module_id,
            project_data=project_data
        )

        # Synchroniser l'XP avec le profil
        if result.get("status") == "success":
            await profile_service.add_xp(
                user_id=current_user.id,
                xp_points=100
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur soumission projet: {str(e)}"
        )


@roadmap_router.get("/statistics", summary="📊 Mes statistiques d'apprentissage")
async def get_my_statistics(
    current_user: UtilisateurRead = Depends(get_current_user)
):
    """
    Récupère vos statistiques globales d'apprentissage.

    Returns:
        - Nombre de cours
        - Cours complétés
        - XP total gagné
        - Temps total passé
        - Moyenne de complétion
    """
    try:
        stats = await roadmap_service.get_user_statistics(current_user.id)

        return {
            "status": "success",
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération statistiques: {str(e)}"
        )

