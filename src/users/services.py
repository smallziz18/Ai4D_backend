from datetime import datetime
from uuid import UUID
from typing import Union, Optional, Dict, Any

from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .utils import generate_password_hash
from src.users.models import Utilisateur, Professeur, Etudiant, StatutUtilisateur
from src.users.schema import ProfesseurCreate, EtudiantCreate, StatutUtilisateur as StatutEnum, UtilisateurCreateBase
from ..error import UserAlreadyExists

class UserService:

    @staticmethod
    async def update_user(user:Utilisateur, user_data: dict, session: AsyncSession):
        for key, value in user_data.items():
            setattr(user, key, value)
        await  session.commit()
        return user


    @staticmethod
    async def get_all_users(session: AsyncSession):
        stmt = select(Utilisateur).order_by(desc(Utilisateur.created_at))
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_user(user_id: UUID, session: AsyncSession):
        stmt = select(Utilisateur).where(Utilisateur.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def user_exists(user_id: UUID, session: AsyncSession) -> bool:
        stmt = select(Utilisateur).where(Utilisateur.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user is not None

    @staticmethod
    # python
    @staticmethod
    async def get_user_by_email(email: str, session: AsyncSession):
        stmt = (
            select(Utilisateur)
            .where(Utilisateur.email == email)
            .options(
                selectinload(Utilisateur.professeur),
                selectinload(Utilisateur.etudiant),
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def email_exists(email: str, session: AsyncSession) -> bool:
        """Vérifie si un email existe déjà"""
        stmt = select(Utilisateur).where(Utilisateur.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user is not None

    @staticmethod
    async def username_exists(username: str, session: AsyncSession) -> bool:
        """Vérifie si un username existe déjà"""
        stmt = select(Utilisateur).where(Utilisateur.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user is not None

    @staticmethod
    async def create_user(
            session: AsyncSession,
            data: Union[EtudiantCreate, ProfesseurCreate, UtilisateurCreateBase]
    ):
        """
        Crée un utilisateur de base SANS profil Etudiant/Professeur.
        Le profil détaillé est créé APRÈS le questionnaire.
        """
        try:
            # L'email est déjà normalisé dans router.py
            normalized_email = str(data.email).strip().lower()

            # Vérifier si l'email existe déjà (avec l'email normalisé)
            if await UserService.email_exists(normalized_email, session):
                raise UserAlreadyExists()

            if await UserService.username_exists(data.username, session):
                raise UserAlreadyExists()

            # Créer UNIQUEMENT l'utilisateur de base
            utilisateur = Utilisateur(
                nom=data.nom,
                prenom=data.prenom,
                username=data.username,
                email=normalized_email,
                motDePasseHash=generate_password_hash(data.motDePasseHash),
                status=data.status,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(utilisateur)

            # Commit final
            await session.commit()
            await session.refresh(utilisateur)

            return utilisateur

        except UserAlreadyExists:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            raise Exception(f"Erreur lors de la création de l'utilisateur: {str(e)}")

    @staticmethod
    async def create_user_with_profile(
            session: AsyncSession,
            data: Union[EtudiantCreate, ProfesseurCreate]
    ):
        """
        ANCIENNE MÉTHODE - Crée un utilisateur avec son profil Etudiant/Professeur.
        ⚠️ DÉPRÉCIÉ: Utilisez create_user() + création du profil après le questionnaire.
        """
        try:
            # L'email est déjà normalisé dans router.py
            normalized_email = str(data.email).strip().lower()

            # Vérifier si l'email existe déjà (avec l'email normalisé)
            if await UserService.email_exists(normalized_email, session):
                raise UserAlreadyExists()

            if await UserService.username_exists(data.username, session):
                raise UserAlreadyExists()

            # Créer l'utilisateur de base
            utilisateur = Utilisateur(
                nom=data.nom,
                prenom=data.prenom,
                username=data.username,
                email=normalized_email,
                motDePasseHash=generate_password_hash(data.motDePasseHash),
                status=data.status,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(utilisateur)

            # Flush pour récupérer l'ID
            await session.flush()

            # Créer le profil spécifique selon le type
            if data.status == StatutEnum.PROFESSEUR:
                professeur = Professeur(
                    id=utilisateur.id,
                    niveau_experience=data.niveau_experience,
                    specialites=data.specialites,
                    motivation_principale=data.motivation_principale,
                    niveau_technologique=data.niveau_technologique,
                )
                session.add(professeur)

            elif data.status == StatutEnum.ETUDIANT:
                etudiant = Etudiant(
                    id=utilisateur.id,
                    niveau_technique=data.niveau_technique,
                    competences=data.competences,
                    objectifs_apprentissage=data.objectifs_apprentissage,
                    motivation=data.motivation,
                    niveau_energie=data.niveau_energie,
                )
                session.add(etudiant)

            else:
                raise ValueError(f"Statut utilisateur inconnu: {data.status}")

            # Commit final
            await session.commit()
            await session.refresh(utilisateur)

            return utilisateur

        except UserAlreadyExists:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            raise Exception(f"Erreur lors de la création de l'utilisateur: {str(e)}")

    @staticmethod
    async def ensure_sql_profile_after_questionnaire(
        user_id: UUID,
        status: StatutEnum,
        details: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None
    ) -> None:
        """
        Crée le profil SQL (Etudiant/Professeur) s'il n'existe pas encore, après le questionnaire initial.
        Les champs sont alimentés par l'analyse LLM si disponible (details), sinon valeurs par défaut sûres.
        """
        from src.db.main import get_session

        close_session = False
        if session is None:
            session = await get_session().__anext__()  # obtenir un AsyncSession
            close_session = True

        try:
            # Vérifier existence utilisateur
            user = await UserService.get_user(user_id, session)
            if not user:
                return

            if status == StatutEnum.ETUDIANT:
                # Profil étudiant
                stmt = select(Etudiant).where(Etudiant.id == user_id)
                res = await session.execute(stmt)
                etu = res.scalar_one_or_none()
                if etu:
                    return
                d = details or {}
                etu = Etudiant(
                    id=user_id,
                    niveau_technique=int(d.get("niveau", d.get("niveau_technique", 3)) or 3),
                    competences=list(d.get("competences", [])) or [],
                    objectifs_apprentissage=d.get("objectifs") or d.get("objectifs_apprentissage"),
                    motivation=d.get("motivation"),
                    niveau_energie=int(d.get("energie", d.get("niveau_energie", 5)) or 5),
                )
                session.add(etu)
                await session.commit()

            elif status == StatutEnum.PROFESSEUR:
                # Profil professeur
                stmt = select(Professeur).where(Professeur.id == user_id)
                res = await session.execute(stmt)
                prof = res.scalar_one_or_none()
                if prof:
                    return
                d = details or {}
                prof = Professeur(
                    id=user_id,
                    niveau_experience=int(d.get("niveau_experience", 1) or 1),
                    specialites=list(d.get("competences", d.get("specialites", [])) or []),
                    motivation_principale=d.get("motivation_principale") or d.get("motivation"),
                    niveau_technologique=int(d.get("niveau_technologique", d.get("energie", 5)) or 5),
                )
                session.add(prof)
                await session.commit()
            else:
                # Autres statuts: ne rien faire
                return
        finally:
            if close_session:
                await session.close()
