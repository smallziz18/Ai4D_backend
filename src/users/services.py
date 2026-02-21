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
        Crée un utilisateur avec son profil Etudiant ou Professeur.
        Le domaine est sauvegardé immédiatement lors de l'inscription.
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
            await session.flush()  # Obtenir l'ID de l'utilisateur

            # Récupérer le domaine et le normaliser en enum
            from src.users.models import Domaine as DomaineEnum

            domaine_raw = getattr(data, 'domaine', 'Général') or 'Général'

            # Convertir en enum si c'est une string
            if isinstance(domaine_raw, str):
                domaine_enum = DomaineEnum.GENERAL  # Default
                for dom in DomaineEnum:
                    if dom.value.lower() == domaine_raw.lower() or dom.name.lower() == domaine_raw.lower():
                        domaine_enum = dom
                        break
            elif isinstance(domaine_raw, DomaineEnum):
                domaine_enum = domaine_raw
            else:
                domaine_enum = DomaineEnum.GENERAL

            # Créer le profil spécifique selon le statut
            if data.status == StatutUtilisateur.ETUDIANT:
                etudiant = Etudiant(
                    id=utilisateur.id,
                    domaine=domaine_enum,  # Utiliser l'enum
                    niveau_technique=5,  # Valeur par défaut, sera mise à jour après questionnaire
                    competences=[],
                    objectifs_apprentissage=None,
                    motivation=None,
                    niveau_energie=5
                )
                session.add(etudiant)

            elif data.status == StatutUtilisateur.PROFESSEUR:
                professeur = Professeur(
                    id=utilisateur.id,
                    domaine=domaine_enum,  # Utiliser l'enum
                    niveau_experience=1,  # Valeur par défaut
                    specialites=[],
                    motivation_principale=None,
                    niveau_technologique=5
                )
                session.add(professeur)

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
        Met à jour le profil SQL (Etudiant/Professeur) avec les détails du questionnaire.
        Le profil existe déjà (créé au signup), on ne fait que mettre à jour les valeurs.
        """
        from src.db.main import get_session

        close_session = False
        if session is None:
            session = await get_session().__anext__()
            close_session = True

        try:
            # Vérifier existence utilisateur
            user = await UserService.get_user(user_id, session)
            if not user:
                return

            d = details or {}

            if status == StatutEnum.ETUDIANT:
                # Mettre à jour le profil étudiant avec les détails du questionnaire
                stmt = select(Etudiant).where(Etudiant.id == user_id)
                res = await session.execute(stmt)
                etu = res.scalar_one_or_none()

                if etu:
                    # Mettre à jour avec les détails du questionnaire
                    etu.niveau_technique = int(d.get("niveau", d.get("niveau_technique", etu.niveau_technique)) or etu.niveau_technique)
                    etu.competences = list(d.get("competences", [])) or etu.competences
                    etu.objectifs_apprentissage = d.get("objectifs") or d.get("objectifs_apprentissage") or etu.objectifs_apprentissage
                    etu.motivation = d.get("motivation") or etu.motivation
                    etu.niveau_energie = int(d.get("energie", d.get("niveau_energie", etu.niveau_energie)) or etu.niveau_energie)
                    await session.commit()

            elif status == StatutEnum.PROFESSEUR:
                # Mettre à jour le profil professeur
                stmt = select(Professeur).where(Professeur.id == user_id)
                res = await session.execute(stmt)
                prof = res.scalar_one_or_none()

                if prof:
                    # Mettre à jour avec les détails du questionnaire
                    prof.niveau_experience = int(d.get("niveau_experience", prof.niveau_experience) or prof.niveau_experience)
                    prof.specialites = list(d.get("competences", d.get("specialites", [])) or prof.specialites)
                    prof.motivation_principale = d.get("motivation_principale") or d.get("motivation") or prof.motivation_principale
                    prof.niveau_technologique = int(d.get("niveau_technologique", d.get("energie", prof.niveau_technologique)) or prof.niveau_technologique)
                    await session.commit()
        finally:
            if close_session:
                await session.close()
