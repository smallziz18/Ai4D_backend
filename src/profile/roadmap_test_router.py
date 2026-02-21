"""
Router pour tester et visualiser les roadmaps générés.
Permet de tester via Postman avec des données JSON.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, Any, List
from uuid import UUID
from pydantic import BaseModel

from src.db.main import get_session
from src.users.dependencies import get_current_user_id

from src.profile.roadmap_services import RoadmapService
from src.profile.services import ProfileService

router = APIRouter(prefix="/api/roadmap-test", tags=["roadmap-test"])


class RoadmapTestRequest(BaseModel):
    """Requête pour tester la génération de roadmap"""
    force_regenerate: bool = False
    duration_weeks: int = 12


class ResourceSearchRequest(BaseModel):
    """Requête pour rechercher des ressources"""
    topic: str
    language: str = "fr"
    user_level: int = 5


@router.post("/generate", response_model=Dict[str, Any])
async def generate_roadmap_test(
    request: RoadmapTestRequest,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Génère une roadmap personnalisée pour l'utilisateur actuel.

    Testable via Postman:
    ```json
    {
        "force_regenerate": true,
        "duration_weeks": 12
    }
    ```
    """
    try:
        # Récupérer le profil utilisateur
        profile_service = ProfileService()
        profil = await profile_service.get_profile_by_user_id(user_id)

        if not profil:
            raise HTTPException(status_code=404, detail="Profil non trouvé. Complétez d'abord le questionnaire initial.")

        # Générer la roadmap
        roadmap_service = RoadmapService()
        roadmap = await roadmap_service.create_and_save_roadmap(
            user_id=user_id,
            profil=profil,
            duration_weeks=request.duration_weeks,
            force_regenerate=request.force_regenerate
        )

        return {
            "success": True,
            "message": "Roadmap générée avec succès",
            "roadmap": roadmap
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération: {str(e)}")
    finally:
        if hasattr(profile_service, '_client'):
            profile_service._client.close()
        if hasattr(roadmap_service, '_client'):
            roadmap_service._client.close()


@router.get("/current", response_model=Dict[str, Any])
async def get_current_roadmap(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Récupère la roadmap active de l'utilisateur.
    """
    try:
        roadmap_service = RoadmapService()
        roadmap = await roadmap_service.get_active_roadmap(user_id)

        if not roadmap:
            return {
                "success": False,
                "message": "Aucune roadmap active trouvée",
                "roadmap": None
            }

        return {
            "success": True,
            "message": "Roadmap récupérée",
            "roadmap": roadmap
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    finally:
        if hasattr(roadmap_service, '_client'):
            roadmap_service._client.close()


@router.post("/search-resources", response_model=Dict[str, Any])
async def search_resources(
    request: ResourceSearchRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Recherche des ressources pour un sujet donné.

    Testable via Postman:
    ```json
    {
        "topic": "CNN",
        "language": "fr",
        "user_level": 5
    }
    ```
    """
    try:
        from src.ai_agents.mcp.web_search_mcp import web_search_mcp

        resources = await web_search_mcp.get_comprehensive_resources(
            topic=request.topic,
            user_level=request.user_level,
            language=request.language,
            include_projects=True
        )

        return {
            "success": True,
            "topic": request.topic,
            "resources": resources,
            "total_videos": len(resources.get("videos", [])),
            "total_cours": len(resources.get("cours", [])),
            "total_articles": len(resources.get("articles", [])),
            "total_projets": len(resources.get("projets", []))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de recherche: {str(e)}")


@router.get("/modules/{course_id}", response_model=Dict[str, Any])
async def get_course_modules(
    course_id: str,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Récupère les modules d'un cours spécifique avec leurs ressources.
    """
    try:
        roadmap_service = RoadmapService()

        course = await roadmap_service.courses_collection.find_one(
            {"course_id": course_id, "user_id": str(user_id)}
        )

        if not course:
            raise HTTPException(status_code=404, detail="Cours non trouvé")

        # Convertir ObjectId en string
        if "_id" in course:
            course["_id"] = str(course["_id"])

        modules = course.get("modules", [])

        return {
            "success": True,
            "course_id": course_id,
            "titre": course.get("titre"),
            "description": course.get("description"),
            "total_modules": len(modules),
            "modules": modules
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    finally:
        if hasattr(roadmap_service, '_client'):
            roadmap_service._client.close()


@router.get("/progression", response_model=Dict[str, Any])
async def get_user_progression(
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Récupère la progression de l'utilisateur sur tous ses cours.
    """
    try:
        roadmap_service = RoadmapService()

        progressions = await roadmap_service.progressions_collection.find(
            {"utilisateur_id": str(user_id)}
        ).to_list(length=100)

        # Convertir ObjectId en string
        for prog in progressions:
            if "_id" in prog:
                prog["_id"] = str(prog["_id"])

        return {
            "success": True,
            "total_courses": len(progressions),
            "progressions": progressions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    finally:
        if hasattr(roadmap_service, '_client'):
            roadmap_service._client.close()

