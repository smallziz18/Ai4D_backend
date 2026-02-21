from typing import List, Optional
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey
import sqlalchemy.dialects.postgresql as pg


class StatutUtilisateur(str, Enum):
    ETUDIANT = "Etudiant"
    PROFESSEUR = "Professeur"
    Administrateur = "Administrateur"


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


class UtilisateurBase(SQLModel):
    nom: str = Field(nullable=False)
    prenom: str = Field(nullable=False)
    username: str = Field(unique=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
    motDePasseHash: str

    # Correction: nom de colonne explicite + type Enum PostgreSQL
    status: StatutUtilisateur = Field(
        sa_column=Column(
            "status",
            pg.ENUM(StatutUtilisateur, name="statututilisateur", create_type=True),
            nullable=False
        )
    )

    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.now)
    )
    updated_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    )
    is_verified: bool = Field(
        sa_column=Column(pg.BOOLEAN, default=False)
    )





class Utilisateur(UtilisateurBase, table=True):
    __tablename__ = "utilisateur"
    id: UUID = Field(
        sa_column=Column(
            pg.UUID,
            primary_key=True,
            default=uuid4
        )
    )

    # Relations vers les tables enfants
    professeur: Optional["Professeur"] = Relationship(back_populates="utilisateur")
    etudiant: Optional["Etudiant"] = Relationship(back_populates="utilisateur")


class Professeur(SQLModel, table=True):
    __tablename__ = "professeur"
    id: UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("utilisateur.id"),
            primary_key=True,
            default=uuid4
        )
    )

    utilisateur: Utilisateur = Relationship(back_populates="professeur")

    domaine: Domaine = Field(
        sa_column=Column(
            pg.ENUM(Domaine, name="domaine", create_type=True),
            nullable=False,
            default=Domaine.GENERAL
        )
    )
    niveau_experience: int = Field(ge=0, le=30, description="Années d'expérience pédagogique")
    specialites: List[str] = Field(
        sa_column=Column(pg.ARRAY(pg.TEXT)), default_factory=list, description="Domaines d'expertise"
    )
    motivation_principale: Optional[str] = None
    niveau_technologique: int = Field(ge=1, le=10)
    def __repr__(self) -> str:
        return f"Professeur(id={self.id})"


class Etudiant(SQLModel, table=True):
    __tablename__ = "etudiant"
    id: UUID = Field(
        sa_column=Column(
            pg.UUID, ForeignKey("utilisateur.id"),
            primary_key=True,
            default=uuid4
        )
    )

    utilisateur: Utilisateur = Relationship(back_populates="etudiant")

    domaine: Domaine = Field(
        sa_column=Column(
            pg.ENUM(Domaine, name="domaine", create_type=True),
            nullable=False,
            default=Domaine.GENERAL
        )
    )
    niveau_technique: int = Field(ge=1, le=10)
    competences: List[str] = Field(
        sa_column=Column(pg.ARRAY(pg.TEXT)), default_factory=list
    )
    objectifs_apprentissage: Optional[str] = None
    motivation: Optional[str] = None
    niveau_energie: int = Field(ge=1, le=10)
    def __repr__(self) -> str:
        return f"Etudiant(id={self.id})"
