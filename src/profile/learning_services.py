"""
Services pour la gestion des cours, progression et chatbot.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, UTC

from src.profile.mongo_models import (
    CourseMongoDB,
    UserProgressionMongoDB,
    ChatConversationMongoDB,
    LearningPathMongoDB
)
from src.db.mongo_db import async_mongo_db


class CourseService:
    """Service de gestion des cours"""

    def __init__(self):
        self.db = async_mongo_db
        self.collection = self.db["courses"]

    async def create_course(self, course_data: Dict[str, Any]) -> str:
        """Créer un nouveau cours"""
        course = CourseMongoDB(**course_data)
        result = await self.collection.insert_one(course.model_dump(by_alias=True, exclude={"id"}))
        return str(result.inserted_id)

    async def get_course(self, course_id: str) -> Optional[CourseMongoDB]:
        """Récupérer un cours par ID"""
        course_doc = await self.collection.find_one({"course_id": course_id})
        if course_doc:
            return CourseMongoDB(**course_doc)
        return None

    async def get_courses_by_level(self, niveau: str) -> List[CourseMongoDB]:
        """Récupérer les cours par niveau"""
        cursor = self.collection.find({"niveau": niveau})
        courses = await cursor.to_list(length=100)
        return [CourseMongoDB(**course) for course in courses]

    async def search_courses(self, tags: List[str], niveau: Optional[str] = None) -> List[CourseMongoDB]:
        """Rechercher des cours par tags"""
        query = {"tags": {"$in": tags}}
        if niveau:
            query["niveau"] = niveau

        cursor = self.collection.find(query)
        courses = await cursor.to_list(length=100)
        return [CourseMongoDB(**course) for course in courses]

    async def update_course(self, course_id: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour un cours"""
        updates["updated_at"] = datetime.now(UTC)
        result = await self.collection.update_one(
            {"course_id": course_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def increment_enrollment(self, course_id: str) -> bool:
        """Incrémenter le nombre d'inscriptions"""
        result = await self.collection.update_one(
            {"course_id": course_id},
            {"$inc": {"total_enrollments": 1}}
        )
        return result.modified_count > 0


class ProgressionService:
    """Service de gestion de la progression utilisateur"""

    def __init__(self):
        self.db = async_mongo_db
        self.collection = self.db["user_progressions"]

    async def create_progression(
        self,
        utilisateur_id: UUID,
        course_id: str
    ) -> str:
        """Créer une nouvelle progression pour un cours"""
        progression = UserProgressionMongoDB(
            utilisateur_id=utilisateur_id,
            course_id=course_id
        )
        result = await self.collection.insert_one(
            progression.model_dump(by_alias=True, exclude={"id"})
        )
        return str(result.inserted_id)

    async def get_progression(
        self,
        utilisateur_id: UUID,
        course_id: str
    ) -> Optional[UserProgressionMongoDB]:
        """Récupérer la progression d'un utilisateur pour un cours"""
        progression_doc = await self.collection.find_one({
            "utilisateur_id": str(utilisateur_id),
            "course_id": course_id
        })
        if progression_doc:
            return UserProgressionMongoDB(**progression_doc)
        return None

    async def get_all_progressions(self, utilisateur_id: UUID) -> List[UserProgressionMongoDB]:
        """Récupérer toutes les progressions d'un utilisateur"""
        cursor = self.collection.find({"utilisateur_id": str(utilisateur_id)})
        progressions = await cursor.to_list(length=100)
        return [UserProgressionMongoDB(**prog) for prog in progressions]

    async def update_progression(
        self,
        utilisateur_id: UUID,
        course_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Mettre à jour la progression"""
        updates["last_activity"] = datetime.now(UTC)
        result = await self.collection.update_one(
            {
                "utilisateur_id": str(utilisateur_id),
                "course_id": course_id
            },
            {"$set": updates}
        )
        return result.modified_count > 0

    async def complete_module(
        self,
        utilisateur_id: UUID,
        course_id: str,
        module_id: str,
        evaluation_result: Dict[str, Any]
    ) -> bool:
        """Marquer un module comme complété"""
        result = await self.collection.update_one(
            {
                "utilisateur_id": str(utilisateur_id),
                "course_id": course_id
            },
            {
                "$addToSet": {"completed_modules": module_id},
                "$set": {
                    f"module_evaluations.{module_id}": evaluation_result,
                    "last_activity": datetime.now(UTC)
                }
            }
        )
        return result.modified_count > 0

    async def complete_lesson(
        self,
        utilisateur_id: UUID,
        course_id: str,
        lesson_id: str
    ) -> bool:
        """Marquer une leçon comme complétée"""
        result = await self.collection.update_one(
            {
                "utilisateur_id": str(utilisateur_id),
                "course_id": course_id
            },
            {
                "$addToSet": {"completed_lessons": lesson_id},
                "$set": {"last_activity": datetime.now(UTC)}
            }
        )
        return result.modified_count > 0

    async def add_time_spent(
        self,
        utilisateur_id: UUID,
        course_id: str,
        minutes: int,
        module_id: Optional[str] = None
    ) -> bool:
        """Ajouter du temps passé sur le cours"""
        update_dict = {
            "$inc": {"total_time_minutes": minutes},
            "$set": {"last_activity": datetime.now(UTC)}
        }

        if module_id:
            update_dict["$inc"][f"time_per_module.{module_id}"] = minutes

        result = await self.collection.update_one(
            {
                "utilisateur_id": str(utilisateur_id),
                "course_id": course_id
            },
            update_dict
        )
        return result.modified_count > 0

    async def calculate_completion_percentage(
        self,
        utilisateur_id: UUID,
        course_id: str,
        total_modules: int
    ) -> float:
        """Calculer le pourcentage de complétion"""
        progression = await self.get_progression(utilisateur_id, course_id)
        if not progression:
            return 0.0

        completed = len(progression.completed_modules)
        percentage = (completed / total_modules) * 100 if total_modules > 0 else 0

        # Mettre à jour le pourcentage
        await self.update_progression(
            utilisateur_id,
            course_id,
            {"completion_percentage": percentage}
        )

        return percentage


class ChatbotService:
    """Service de gestion des conversations chatbot"""

    def __init__(self):
        self.db = async_mongo_db
        self.collection = self.db["chat_conversations"]

    async def create_conversation(
        self,
        utilisateur_id: UUID,
        session_id: str,
        context_snapshot: Dict[str, Any]
    ) -> str:
        """Créer une nouvelle conversation"""
        conversation = ChatConversationMongoDB(
            utilisateur_id=utilisateur_id,
            session_id=session_id,
            context_snapshot=context_snapshot
        )
        result = await self.collection.insert_one(
            conversation.model_dump(by_alias=True, exclude={"id"})
        )
        return str(result.inserted_id)

    async def get_conversation(
        self,
        utilisateur_id: UUID,
        session_id: str
    ) -> Optional[ChatConversationMongoDB]:
        """Récupérer une conversation"""
        conversation_doc = await self.collection.find_one({
            "utilisateur_id": str(utilisateur_id),
            "session_id": session_id
        })
        if conversation_doc:
            return ChatConversationMongoDB(**conversation_doc)
        return None

    async def add_message(
        self,
        utilisateur_id: UUID,
        session_id: str,
        role: str,
        content: str,
        intention: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Ajouter un message à la conversation"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
            "intention": intention or {}
        }

        # Extraire les topics si intention présente
        topics_to_add = []
        if intention and "primary" in intention:
            topics_to_add.append(intention["primary"])

        update_dict = {
            "$push": {"messages": message},
            "$inc": {"total_messages": 1},
            "$set": {"last_message_at": datetime.now(UTC)}
        }

        if topics_to_add:
            update_dict["$addToSet"] = {
                "intentions_detected": {"$each": topics_to_add}
            }

        result = await self.collection.update_one(
            {
                "utilisateur_id": str(utilisateur_id),
                "session_id": session_id
            },
            update_dict,
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def get_recent_conversations(
        self,
        utilisateur_id: UUID,
        limit: int = 10
    ) -> List[ChatConversationMongoDB]:
        """Récupérer les conversations récentes"""
        cursor = self.collection.find(
            {"utilisateur_id": str(utilisateur_id)}
        ).sort("last_message_at", -1).limit(limit)

        conversations = await cursor.to_list(length=limit)
        return [ChatConversationMongoDB(**conv) for conv in conversations]

    async def mark_resolved(
        self,
        utilisateur_id: UUID,
        session_id: str,
        satisfaction: int
    ) -> bool:
        """Marquer une conversation comme résolue"""
        result = await self.collection.update_one(
            {
                "utilisateur_id": str(utilisateur_id),
                "session_id": session_id
            },
            {
                "$set": {
                    "resolved": True,
                    "user_satisfaction": satisfaction
                }
            }
        )
        return result.modified_count > 0


class LearningPathService:
    """Service de gestion des parcours d'apprentissage"""

    def __init__(self):
        self.db = async_mongo_db
        self.collection = self.db["learning_paths"]

    async def create_learning_path(
        self,
        utilisateur_id: UUID,
        learning_path_data: Dict[str, Any]
    ) -> str:
        """Créer un nouveau parcours d'apprentissage"""
        learning_path = LearningPathMongoDB(
            utilisateur_id=utilisateur_id,
            **learning_path_data
        )
        result = await self.collection.insert_one(
            learning_path.model_dump(by_alias=True, exclude={"id"})
        )
        return str(result.inserted_id)

    async def get_learning_path(self, utilisateur_id: UUID) -> Optional[LearningPathMongoDB]:
        """Récupérer le parcours d'apprentissage d'un utilisateur"""
        path_doc = await self.collection.find_one(
            {"utilisateur_id": str(utilisateur_id)}
        )
        if path_doc:
            return LearningPathMongoDB(**path_doc)
        return None

    async def complete_quest(
        self,
        utilisateur_id: UUID,
        quest_id: str,
        xp_earned: int
    ) -> bool:
        """Marquer une quête comme complétée"""
        result = await self.collection.update_one(
            {"utilisateur_id": str(utilisateur_id)},
            {
                "$addToSet": {"quetes_completed": quest_id},
                "$inc": {"xp_earned": xp_earned},
                "$set": {"updated_at": datetime.now(UTC)}
            }
        )
        return result.modified_count > 0

    async def unlock_skill(self, utilisateur_id: UUID, skill_id: str) -> bool:
        """Débloquer une compétence dans le skill tree"""
        result = await self.collection.update_one(
            {"utilisateur_id": str(utilisateur_id)},
            {
                "$addToSet": {"unlocked_skills": skill_id},
                "$set": {"updated_at": datetime.now(UTC)}
            }
        )
        return result.modified_count > 0

    async def earn_badge(self, utilisateur_id: UUID, badge: str) -> bool:
        """Gagner un badge"""
        result = await self.collection.update_one(
            {"utilisateur_id": str(utilisateur_id)},
            {
                "$addToSet": {"badges_earned": badge},
                "$set": {"updated_at": datetime.now(UTC)}
            }
        )
        return result.modified_count > 0

    async def update_level(self, utilisateur_id: UUID, new_level: int) -> bool:
        """Mettre à jour le niveau"""
        result = await self.collection.update_one(
            {"utilisateur_id": str(utilisateur_id)},
            {
                "$set": {
                    "current_level": new_level,
                    "updated_at": datetime.now(UTC)
                }
            }
        )
        return result.modified_count > 0


# Instances globales
course_service = CourseService()
progression_service = ProgressionService()
chatbot_service = ChatbotService()
learning_path_service = LearningPathService()

