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
