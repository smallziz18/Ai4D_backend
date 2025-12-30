"""
Services de gestion des roadmaps et progression utilisateur.
Gère la création, le suivi et la validation des roadmaps personnalisées.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, UTC
from uuid import UUID
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from bson import ObjectId

from src.db.mongo_db import get_mongo_db
from src.profile.mongo_models import (
    CourseMongoDB,
    UserProgressionMongoDB,
    ProfilMongoDB
)
from src.ai_agents.agents.course_recommendation_agent import course_recommendation_agent

logger = logging.getLogger(__name__)


class RoadmapService:
    """Service de gestion des roadmaps personnalisées"""

    def __init__(self):
        self.db: AsyncIOMotorDatabase = get_mongo_db()
        self.courses_collection = self.db["courses"]
        self.progressions_collection = self.db["user_progressions"]
        self.profiles_collection = self.db["profils"]

    def _convert_uuids_to_strings(self, obj: Any) -> Any:
        """
        Convertir récursivement tous les UUID et ObjectId en strings dans un objet.
        Nécessaire pour la compatibilité MongoDB et la sérialisation JSON.
        """
        from bson import ObjectId

        if isinstance(obj, (UUID, ObjectId)):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_uuids_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_uuids_to_strings(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj  # Garder les datetime tels quels, FastAPI les sérialisera
        else:
            return obj

    async def create_and_save_roadmap(
        self,
        user_id: UUID,
        profil: ProfilMongoDB,
        duration_weeks: int = 12,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Créer et sauvegarder une roadmap personnalisée pour l'utilisateur.

        Args:
            user_id: ID de l'utilisateur
            profil: Profil complet de l'utilisateur
            duration_weeks: Durée en semaines
            force_regenerate: Forcer la régénération si une roadmap existe

        Returns:
            Roadmap complète avec ID de cours
        """
        try:
            # Vérifier si une roadmap récente existe
            if not force_regenerate:
                existing = await self.get_active_roadmap(user_id)
                if existing:
                    logger.info(f"Roadmap existante trouvée pour {user_id}")
                    return existing

            # Construire les objectifs
            objectives = self._build_objectives(profil)

            # Extraire les faiblesses
            weaknesses_context = self._extract_weaknesses(profil)
            if weaknesses_context:
                objectives += weaknesses_context

            # Générer la roadmap avec l'agent
            roadmap = await course_recommendation_agent.create_learning_roadmap(
                user_level=profil.niveau,
                user_objectives=objectives,
                user_competences=profil.competences if profil.competences else [],
                duration_weeks=duration_weeks
            )

            # Créer l'objet cours
            course_data = self._prepare_course_data(roadmap, profil, duration_weeks)

            # Convertir tous les UUID en strings récursivement
            course_data = self._convert_uuids_to_strings(course_data)

            # Sauvegarder dans MongoDB
            result = await self.courses_collection.insert_one(course_data)
            course_id = str(result.inserted_id)

            # Créer la progression initiale
            await self._create_initial_progression(user_id, course_data["course_id"], course_data)

            # Enrichir course_data avec profil utilisateur
            course_data["profil_utilisateur"] = {
                "niveau": profil.niveau,
                "xp": profil.xp,
                "badges": profil.badges,
                "competences_actuelles": profil.competences,
                "energie_actuelle": profil.energie,
                "objectifs": profil.objectifs
            }

            # Ajouter l'ObjectId converti en string
            course_data["_id"] = course_id

            logger.info(f"Roadmap créée avec succès: {course_data['course_id']}")
            return course_data

        except Exception as e:
            logger.error(f"Erreur création roadmap: {str(e)}")
            raise Exception(f"Erreur création roadmap: {str(e)}")

    def _build_objectives(self, profil: ProfilMongoDB) -> str:
        """Construire les objectifs basés sur le profil"""
        if profil.objectifs:
            return profil.objectifs

        # Objectifs par défaut basés sur le niveau
        if profil.niveau <= 3:
            return "Maîtriser les fondamentaux du Machine Learning et faire mes premiers projets"
        elif profil.niveau <= 6:
            return "Approfondir mes connaissances en Deep Learning et réaliser des projets avancés"
        else:
            return "Me spécialiser dans les architectures modernes (Transformers, LLM) et contribuer à la recherche"

    def _extract_weaknesses(self, profil: ProfilMongoDB) -> str:
        """Extraire les faiblesses identifiées"""
        weaknesses = []

        if hasattr(profil, 'analyse_questions_ouvertes') and profil.analyse_questions_ouvertes:
            # Vérifier si c'est un dict ou une liste
            analyses = profil.analyse_questions_ouvertes

            if isinstance(analyses, dict):
                analyses = [analyses]
            elif not isinstance(analyses, list):
                return ""

            for analysis in analyses:
                if isinstance(analysis, dict):
                    score = analysis.get('score_moyen', 10)
                    if score < 6:
                        concept = analysis.get('concept_principal', '')
                        if concept:
                            weaknesses.append(concept)

        if weaknesses:
            return f"\n\n⚠️ PRIORITÉS (faiblesses identifiées) : {', '.join(weaknesses[:5])}"
        return ""

    def _prepare_course_data(
        self,
        roadmap: Dict[str, Any],
        profil: ProfilMongoDB,
        duration_weeks: int
    ) -> Dict[str, Any]:
        """Préparer les données du cours pour MongoDB"""
        # S'assurer que utilisateur_id est une string
        user_id_str = str(profil.utilisateur_id)
        course_id = f"roadmap_{user_id_str}_{int(datetime.now(UTC).timestamp())}"

        # Extraire les modules (peut être phases ou roadmap_suggeree)
        modules = (
            roadmap.get("phases", []) or
            roadmap.get("modules", []) or
            roadmap.get("roadmap_suggeree", []) or
            []
        )

        # Si pas de modules, créer un module par défaut
        if not modules:
            modules = [{
                "id": "module_1",
                "titre": "Introduction au Machine Learning",
                "description": "Découvrir les concepts fondamentaux",
                "duree": "2 semaines",
                "ordre": 1,
                "lessons": []
            }]

        # S'assurer que chaque module a un ID
        for i, module in enumerate(modules):
            if not module.get("id"):
                module["id"] = f"module_{i+1}"
            if not module.get("ordre"):
                module["ordre"] = i + 1

        return {
            "course_id": course_id,
            "titre": roadmap.get("titre") or f"🎯 Ma Roadmap Personnalisée - Niveau {profil.niveau}",
            "description": roadmap.get("description") or f"Roadmap IA adaptée à votre profil et vos objectifs : {profil.objectifs[:100] if profil.objectifs else 'Progresser en Machine Learning'}",
            "niveau": self._get_niveau_label(profil.niveau),
            "duree_totale": f"{duration_weeks} semaines",
            "objectifs": roadmap.get("objectifs", [profil.objectifs]) if profil.objectifs else ["Maîtriser le Machine Learning"],
            "prerequis": roadmap.get("prerequis", ["Bases en Python", "Mathématiques niveau lycée"]),
            "tags": roadmap.get("tags", ["machine-learning", "ia", "personnalisé", f"niveau-{profil.niveau}"]),
            "modules": modules,
            "ressources_globales": roadmap.get("ressources_supplementaires", {}),
            "evaluation_finale": roadmap.get("evaluation_finale"),
            "created_by": "CourseRecommendationAgent",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "total_enrollments": 1,
            "average_rating": 0.0,
            "user_specific": True,
            "user_id": user_id_str  # Déjà converti en string
        }

    def _get_niveau_label(self, niveau: int) -> str:
        """Convertir niveau numérique en label"""
        if niveau <= 3:
            return "Débutant"
        elif niveau <= 6:
            return "Intermédiaire"
        elif niveau <= 8:
            return "Avancé"
        else:
            return "Expert"

    async def _create_initial_progression(
        self,
        user_id: UUID,
        course_id: str,
        roadmap: Dict[str, Any]
    ):
        """Créer la progression initiale pour un cours"""
        modules = roadmap.get("phases", []) or roadmap.get("modules", [])
        first_module_id = modules[0].get("id") if modules else None

        progression = {
            "utilisateur_id": user_id,
            "course_id": course_id,
            "started_at": datetime.now(UTC),
            "last_activity": datetime.now(UTC),
            "completion_percentage": 0.0,
            "estimated_completion_date": datetime.now(UTC) + timedelta(weeks=12),
            "completed_modules": [],
            "current_module": first_module_id,
            "completed_lessons": [],
            "current_lesson": None,
            "module_evaluations": {},
            "completed_projects": [],
            "total_time_minutes": 0,
            "time_per_module": {},
            "xp_earned_course": 0,
            "badges_earned_course": [],
            "user_notes": [],
            "user_rating": None,
            "user_feedback": None
        }

        # Convertir tous les UUID en strings récursivement
        progression = self._convert_uuids_to_strings(progression)

        await self.progressions_collection.insert_one(progression)

    async def get_active_roadmap(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Récupérer la roadmap active de l'utilisateur"""
        user_id_str = str(user_id)

        # Trouver la roadmap la plus récente non complétée
        cursor = self.progressions_collection.find(
            {
                "utilisateur_id": user_id_str,
                "completion_percentage": {"$lt": 100.0}
            }
        ).sort("started_at", -1).limit(1)

        progressions = await cursor.to_list(length=1)

        if not progressions:
            return None

        progression = progressions[0]

        # Récupérer le cours associé
        course = await self.courses_collection.find_one(
            {"course_id": progression["course_id"]}
        )

        if not course:
            return None

        # Enrichir avec la progression
        course["progression"] = {
            "completion_percentage": progression["completion_percentage"],
            "current_module": progression["current_module"],
            "completed_modules": progression["completed_modules"],
            "xp_earned": progression["xp_earned_course"],
            "time_spent_minutes": progression["total_time_minutes"]
        }

        # Convertir tous les ObjectId et UUID en strings pour la sérialisation JSON
        course = self._convert_uuids_to_strings(course)

        return course

    async def get_user_progression(
        self,
        user_id: UUID,
        course_id: str
    ) -> Optional[Dict[str, Any]]:
        """Récupérer la progression d'un utilisateur pour un cours"""
        progression = await self.progressions_collection.find_one({
            "utilisateur_id": str(user_id),  # Convertir UUID en string
            "course_id": course_id
        })

        if progression:
            # Convertir tous les ObjectId et UUID en strings
            progression = self._convert_uuids_to_strings(progression)

        return progression

    async def update_module_progress(
        self,
        user_id: UUID,
        course_id: str,
        module_id: str,
        lesson_id: Optional[str] = None,
        time_spent_minutes: int = 0
    ) -> Dict[str, Any]:
        """Mettre à jour la progression d'un module"""
        try:
            update_data = {
                "last_activity": datetime.now(UTC),
                "current_module": module_id,
                f"time_per_module.{module_id}": time_spent_minutes
            }

            if lesson_id:
                update_data["current_lesson"] = lesson_id

            # Incrémenter le temps total
            await self.progressions_collection.update_one(
                {
                    "utilisateur_id": str(user_id),  # Convertir UUID en string
                    "course_id": course_id
                },
                {
                    "$set": update_data,
                    "$inc": {"total_time_minutes": time_spent_minutes}
                }
            )

            return {"status": "success", "message": "Progression mise à jour"}

        except Exception as e:
            logger.error(f"Erreur update progression: {str(e)}")
            raise

    async def complete_lesson(
        self,
        user_id: UUID,
        course_id: str,
        lesson_id: str,
        xp_earned: int = 10
    ) -> Dict[str, Any]:
        """Marquer une leçon comme complétée"""
        try:
            result = await self.progressions_collection.update_one(
                {
                    "utilisateur_id": str(user_id),  # Convertir UUID en string
                    "course_id": course_id,
                    "completed_lessons": {"$ne": lesson_id}  # Éviter les doublons
                },
                {
                    "$addToSet": {"completed_lessons": lesson_id},
                    "$inc": {"xp_earned_course": xp_earned},
                    "$set": {"last_activity": datetime.now(UTC)}
                }
            )

            if result.modified_count > 0:
                # Mettre à jour le pourcentage de complétion
                await self._update_completion_percentage(user_id, course_id)

                return {
                    "status": "success",
                    "message": f"Leçon complétée ! +{xp_earned} XP",
                    "xp_earned": xp_earned
                }

            return {"status": "already_completed", "message": "Leçon déjà complétée"}

        except Exception as e:
            logger.error(f"Erreur complétion leçon: {str(e)}")
            raise

    async def complete_module(
        self,
        user_id: UUID,
        course_id: str,
        module_id: str,
        evaluation_score: float,
        xp_earned: int = 50
    ) -> Dict[str, Any]:
        """Marquer un module comme complété avec évaluation"""
        try:
            passed = evaluation_score >= 70.0

            result = await self.progressions_collection.update_one(
                {
                    "utilisateur_id": str(user_id),  # Convertir UUID en string
                    "course_id": course_id,
                    "completed_modules": {"$ne": module_id}
                },
                {
                    "$addToSet": {"completed_modules": module_id},
                    "$set": {
                        f"module_evaluations.{module_id}": {
                            "score": evaluation_score,
                            "passed": passed,
                            "date": datetime.now(UTC).isoformat(),
                            "attempts": 1
                        },
                        "last_activity": datetime.now(UTC)
                    },
                    "$inc": {"xp_earned_course": xp_earned if passed else 0}
                }
            )

            if result.modified_count > 0:
                # Mettre à jour le pourcentage
                await self._update_completion_percentage(user_id, course_id)

                # Débloquer le module suivant
                next_module = await self._get_next_module(course_id, module_id)

                if next_module:
                    await self.progressions_collection.update_one(
                        {"utilisateur_id": str(user_id), "course_id": course_id},  # Convertir UUID en string
                        {"$set": {"current_module": next_module["id"]}}
                    )

                return {
                    "status": "success",
                    "passed": passed,
                    "score": evaluation_score,
                    "xp_earned": xp_earned if passed else 0,
                    "next_module": next_module,
                    "message": f"🎉 Module complété ! Score: {evaluation_score}%" if passed else "Module échoué. Réessayez !"
                }

            return {"status": "already_completed", "message": "Module déjà complété"}

        except Exception as e:
            logger.error(f"Erreur complétion module: {str(e)}")
            raise

    async def _update_completion_percentage(self, user_id: UUID, course_id: str):
        """Calculer et mettre à jour le pourcentage de complétion"""
        progression = await self.progressions_collection.find_one({
            "utilisateur_id": str(user_id),  # Convertir UUID en string
            "course_id": course_id
        })

        course = await self.courses_collection.find_one({"course_id": course_id})

        if not progression or not course:
            return

        total_modules = len(course.get("modules", []))
        completed_modules = len(progression.get("completed_modules", []))

        if total_modules > 0:
            percentage = (completed_modules / total_modules) * 100

            await self.progressions_collection.update_one(
                {"utilisateur_id": str(user_id), "course_id": course_id},  # Convertir UUID en string
                {"$set": {"completion_percentage": round(percentage, 2)}}
            )

    async def _get_next_module(
        self,
        course_id: str,
        current_module_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtenir le module suivant"""
        course = await self.courses_collection.find_one({"course_id": course_id})

        if not course:
            return None

        modules = course.get("modules", [])

        for i, module in enumerate(modules):
            if module.get("id") == current_module_id:
                if i + 1 < len(modules):
                    return modules[i + 1]
                break

        return None

    async def add_user_note(
        self,
        user_id: UUID,
        course_id: str,
        module_id: str,
        note_content: str
    ) -> Dict[str, Any]:
        """Ajouter une note utilisateur"""
        note = {
            "module_id": module_id,
            "content": note_content,
            "created_at": datetime.now(UTC).isoformat()
        }

        await self.progressions_collection.update_one(
            {"utilisateur_id": str(user_id), "course_id": course_id},  # Convertir UUID en string
            {"$push": {"user_notes": note}}
        )

        return {"status": "success", "message": "Note ajoutée"}

    async def submit_project(
        self,
        user_id: UUID,
        course_id: str,
        module_id: str,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Soumettre un projet de module"""
        project = {
            "module_id": module_id,
            "title": project_data.get("title"),
            "description": project_data.get("description"),
            "github_url": project_data.get("github_url"),
            "submitted_at": datetime.now(UTC).isoformat(),
            "status": "submitted"
        }

        result = await self.progressions_collection.update_one(
            {"utilisateur_id": str(user_id), "course_id": course_id},  # Convertir UUID en string
            {
                "$push": {"completed_projects": project},
                "$inc": {"xp_earned_course": 100},  # Bonus XP pour projet
                "$set": {"last_activity": datetime.now(UTC)}
            }
        )

        if result.modified_count > 0:
            return {
                "status": "success",
                "message": "🚀 Projet soumis ! +100 XP",
                "xp_earned": 100
            }

        return {"status": "error", "message": "Erreur soumission projet"}

    async def get_user_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Obtenir les statistiques globales de l'utilisateur"""
        progressions = await self.progressions_collection.find({
            "utilisateur_id": str(user_id)  # Convertir UUID en string
        }).to_list(length=None)

        total_courses = len(progressions)
        completed_courses = sum(1 for p in progressions if p.get("completion_percentage", 0) >= 100)
        total_xp = sum(p.get("xp_earned_course", 0) for p in progressions)
        total_time = sum(p.get("total_time_minutes", 0) for p in progressions)

        return {
            "total_courses": total_courses,
            "completed_courses": completed_courses,
            "in_progress_courses": total_courses - completed_courses,
            "total_xp_earned": total_xp,
            "total_time_hours": round(total_time / 60, 1),
            "average_completion": round(
                sum(p.get("completion_percentage", 0) for p in progressions) / total_courses if total_courses > 0 else 0,
                2
            )
        }


# Instance globale
roadmap_service = RoadmapService()

