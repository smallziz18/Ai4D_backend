from typing import List, Optional
from uuid import UUID
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator




# -------- ENUM --------

class StatutUtilisateur(str, Enum):
    ETUDIANT = "Etudiant"
    PROFESSEUR = "Professeur"


class Domaine(str, Enum):
    INFORMATIQUE = "Informatique"
    DATA_SCIENCE = "Data Science"
    DROIT = "Droit"
    MARKETING = "Marketing"
    CHIMIE = "Chimie"
    PHYSIQUE = "Physique"
    MEDECINE = "Médecine"
    BIOLOGIE = "Biologie"
    ECONOMIE = "Économie"
    MANAGEMENT = "Management"
    GENERAL = "Général"


# -------- BASE COMMUNE --------

class UtilisateurBase(BaseModel):
    nom: str
    prenom: str
    username: str
    email: EmailStr
    motDePasseHash: str
    status: StatutUtilisateur


# -------- SCHÉMAS DE CRÉATION --------

class UtilisateurCreateBase(BaseModel):
    """
    Schéma de création de base pour le signup.
    Ne contient QUE les données minimales de l'utilisateur.
    Le profil détaillé (Etudiant/Professeur) sera créé APRÈS le questionnaire.
    """
    nom: str
    prenom: str
    username: str
    email: EmailStr
    motDePasseHash: str
    status: StatutUtilisateur
    domaine: Optional[str] = "Général"  # Accepter string directement


class ProfesseurCreate(UtilisateurBase):
    status: StatutUtilisateur = StatutUtilisateur.PROFESSEUR
    domaine: Optional[str] = "Général"
    niveau_experience: int = Field(ge=0, le=20)
    specialites: List[str]
    motivation_principale: Optional[str]
    niveau_technologique: int = Field(ge=1, le=10)


class EtudiantCreate(UtilisateurBase):
    status: StatutUtilisateur = StatutUtilisateur.ETUDIANT
    domaine: Optional[str] = "Général"
    niveau_technique: int = Field(ge=1, le=10)
    competences: List[str]
    objectifs_apprentissage: Optional[str]
    motivation: Optional[str]
    niveau_energie: int = Field(ge=1, le=10)





# -------- SCHÉMAS DE LECTURE (GET) --------

class UtilisateurRead(BaseModel):
    id: UUID
    nom: str
    prenom: str
    username: str
    email: EmailStr
    status: StatutUtilisateur
    domaine: Optional[str] = "Général"  # String, pas Enum !
    created_at: datetime
    updated_at: datetime
    # ...existing code...
    niveau_technique: Optional[int] = None
    competences: Optional[List[str]] = None
    objectifs_apprentissage: Optional[str] = None
    motivation: Optional[str] = None
    niveau_energie: Optional[int] = None
    niveau_experience: Optional[int] = None
    specialites: Optional[List[str]] = None
    motivation_principale: Optional[str] = None
    niveau_technologique: Optional[int] = None

    class Config:
        from_attributes = True


class ProfesseurRead(UtilisateurRead):
    niveau_experience: int
    specialites: List[str]
    motivation_principale: Optional[str]
    niveau_technologique: int


class EtudiantRead(UtilisateurRead):
    domaine: Optional[str] = "Général"  # String, pas Enum
    niveau_technique: int
    competences: List[str]
    objectifs_apprentissage: Optional[str]
    motivation: Optional[str]
    niveau_energie: int


# ...existing code...
class UserLogin(BaseModel):
    email: EmailStr
    password: str



class EmailModel(BaseModel):
    mails: List[EmailStr]
    subject: str
    body: str
    subtype: Optional[str] = "html"


class PasswordResetModel(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    new_password: str
    confirm_new_password: str


