from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Field


class ProfilCreate(BaseModel):
    """Schema pour la création d'un profil"""
    utilisateur_id: UUID
    domaine: str = "Général"
    niveau: int = 1
    xp: int = 0
    badges: List[str] = Field(default_factory=list)
    competences: List[str] = Field(default_factory=list)
    objectifs: Optional[str] = None
    motivation: Optional[str] = None
    energie: int = 5
    preferences: Dict[str, Any] = Field(default_factory=dict)
    recommandations: Optional[List[str]] = Field(default_factory=list)
    analyse_detaillee: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProfilUpdate(BaseModel):
    """Schema pour la mise à jour d'un profil"""
    niveau: Optional[int] = None
    xp: Optional[int] = None
    badges: Optional[List[str]] = None
    competences: Optional[List[str]] = None
    objectifs: Optional[str] = None
    motivation: Optional[str] = None
    energie: Optional[int] = None
    preferences: Optional[Dict[str, Any]] = None
    recommandations: Optional[List[str]] = None
    analyse_detaillee: Optional[Dict[str, Any]] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class ProfilResponse(BaseModel):
    """Schema pour la réponse API"""
    id: str
    utilisateur_id: UUID
    domaine: str
    niveau: int
    xp: int
    badges: List[str]
    competences: List[str]
    objectifs: Optional[str]
    motivation: Optional[str]
    energie: int
    preferences: Dict[str, Any]
    recommandations: Optional[List[str]] = Field(default_factory=list)
    analyse_detaillee: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime







class XPRequest(BaseModel):
    xp_points: int

class BadgeRequest(BaseModel):
    badge: str

class CompetenceRequest(BaseModel):
    competence: str

class PreferencesRequest(BaseModel):
    preferences: Dict[str, Any]

class ActivityRequest(BaseModel):
    activity_type: str
    xp_reward: int = 0

class AchievementRequest(BaseModel):
    achievement: str
    badge: str = None