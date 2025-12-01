from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, BeforeValidator
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, handler):  # Ajout du paramètre handler
        if not isinstance(v, (str, ObjectId)):
            raise ValueError("Invalid ObjectId")
        if isinstance(v, str) and not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(ObjectId(v))

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


# Type annoté pour ObjectId
PyObjectIdAnnotated = Annotated[PyObjectId, BeforeValidator(PyObjectId.validate)]


class ProfilMongoDB(BaseModel):
    """Modèle Profil pour MongoDB"""
    id: Optional[PyObjectIdAnnotated] = Field(default_factory=PyObjectId, alias="_id")
    utilisateur_id: UUID
    niveau: int = Field(default=1, ge=1)
    xp: int = Field(default=0, ge=0)
    badges: List[str] = Field(default_factory=list)
    competences: List[str] = Field(default_factory=list)
    objectifs: Optional[str] = None
    motivation: Optional[str] = None
    energie: int = Field(default=5, ge=1, le=10)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    recommandations: Optional[List[str]] = Field(default_factory=list)  # Nouveau champ
    analyse_detaillee: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Nouveau champ
    historique_activites: List[Dict[str, Any]] = Field(default_factory=list)
    statistiques: Dict[str, Any] = Field(default_factory=dict)

    # Gamification
    current_streak: int = Field(default=0, ge=0)  # Série de jours consécutifs
    best_streak: int = Field(default=0, ge=0)  # Meilleure série
    last_activity_date: Optional[datetime] = None  # Dernière activité
    quiz_completed: int = Field(default=0, ge=0)  # Nombre de quiz complétés
    perfect_quiz_count: int = Field(default=0, ge=0)  # Nombre de quiz parfaits
    total_xp_earned: int = Field(default=0, ge=0)  # XP total gagné

    # Questionnaire initial de profilage
    questionnaire_initial_complete: bool = Field(default=False)  # Si le questionnaire initial a été fait
    questionnaire_initial_date: Optional[datetime] = None  # Date du questionnaire initial
    questionnaire_reponses: List[Dict[str, Any]] = Field(default_factory=list)  # Réponses détaillées
    analyse_questions_ouvertes: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Analyse des questions ouvertes

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class CourseMongoDB(BaseModel):
    """Modèle Cours pour MongoDB"""
    id: Optional[PyObjectIdAnnotated] = Field(default_factory=PyObjectId, alias="_id")
    course_id: str  # ID unique du cours
    titre: str
    description: str
    niveau: str  # Débutant, Intermédiaire, Avancé
    duree_totale: str  # "6 semaines", "40 heures", etc.
    objectifs: List[str] = Field(default_factory=list)
    prerequis: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Structure du cours
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    ressources_globales: Dict[str, Any] = Field(default_factory=dict)
    evaluation_finale: Optional[Dict[str, Any]] = None

    # Métadonnées
    created_by: str = "CourseManagerAgent"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    total_enrollments: int = Field(default=0, ge=0)
    average_rating: float = Field(default=0.0, ge=0.0, le=5.0)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class UserProgressionMongoDB(BaseModel):
    """Modèle Progression Utilisateur pour MongoDB"""
    id: Optional[PyObjectIdAnnotated] = Field(default_factory=PyObjectId, alias="_id")
    utilisateur_id: UUID
    course_id: str

    # Progression globale
    started_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    estimated_completion_date: Optional[datetime] = None

    # Modules complétés
    completed_modules: List[str] = Field(default_factory=list)
    current_module: Optional[str] = None

    # Leçons complétées
    completed_lessons: List[str] = Field(default_factory=list)
    current_lesson: Optional[str] = None

    # Évaluations
    module_evaluations: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    # Format: {"module_1": {"score": 85, "passed": true, "attempts": 2, "date": "..."}}

    # Projets
    completed_projects: List[Dict[str, Any]] = Field(default_factory=list)

    # Temps passé
    total_time_minutes: int = Field(default=0, ge=0)
    time_per_module: Dict[str, int] = Field(default_factory=dict)

    # Gamification
    xp_earned_course: int = Field(default=0, ge=0)
    badges_earned_course: List[str] = Field(default_factory=list)

    # Notes et feedback utilisateur
    user_notes: List[Dict[str, Any]] = Field(default_factory=list)
    user_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    user_feedback: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str, UUID: str}
    }


class ChatConversationMongoDB(BaseModel):
    """Modèle Conversation Chatbot pour MongoDB"""
    id: Optional[PyObjectIdAnnotated] = Field(default_factory=PyObjectId, alias="_id")
    utilisateur_id: UUID
    session_id: str

    # Métadonnées conversation
    started_at: datetime = Field(default_factory=datetime.now)
    last_message_at: datetime = Field(default_factory=datetime.now)
    total_messages: int = Field(default=0, ge=0)

    # Messages
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    # Format: {"role": "user|assistant", "content": "...", "timestamp": "...", "intention": {...}}

    # Contexte
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)
    # Snapshot du contexte utilisateur au début de la conversation

    # Tags et catégorisation
    topics_discussed: List[str] = Field(default_factory=list)
    intentions_detected: List[str] = Field(default_factory=list)

    # Satisfaction
    user_satisfaction: Optional[int] = Field(default=None, ge=1, le=5)
    resolved: bool = Field(default=False)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str, UUID: str}
    }


class LearningPathMongoDB(BaseModel):
    """Modèle Parcours d'Apprentissage pour MongoDB"""
    id: Optional[PyObjectIdAnnotated] = Field(default_factory=PyObjectId, alias="_id")
    utilisateur_id: UUID

    # Parcours global
    parcours_global: Dict[str, Any] = Field(default_factory=dict)

    # Quêtes
    quetes_principales: List[Dict[str, Any]] = Field(default_factory=list)
    quetes_secondaires: List[Dict[str, Any]] = Field(default_factory=list)
    boss_fights: List[Dict[str, Any]] = Field(default_factory=list)

    # Progression
    quetes_completed: List[str] = Field(default_factory=list)
    current_quest: Optional[str] = None

    # Skill Tree
    skill_tree: Dict[str, Any] = Field(default_factory=dict)
    unlocked_skills: List[str] = Field(default_factory=list)

    # XP et niveau
    total_xp_available: int = Field(default=0, ge=0)
    xp_earned: int = Field(default=0, ge=0)
    current_level: int = Field(default=1, ge=1)

    # Badges
    badges_earned: List[str] = Field(default_factory=list)

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "TutoringAgent"

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str, UUID: str}
    }

