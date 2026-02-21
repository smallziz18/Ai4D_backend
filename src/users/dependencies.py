from typing import List
import logging

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, HTTPException, status, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from .schema import UtilisateurRead
from src.users.utils import decode_token
from src.db.redis import is_jti_in_blocklist
from src.db.main import get_session
from .services import UserService
from src.error import (
    RevokedToken,
    InvalidToken,
    AccessTokenRequired,
    RefreshTokenRequired,
    UserNotFound, EmailNotVerified
)

logger = logging.getLogger("dependencies")
users_service = UserService()


class AccessToken(HTTPBearer):
    """Classe de base pour la gestion des tokens JWT"""

    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        creds: HTTPAuthorizationCredentials = await super().__call__(request)
        if not creds or not creds.credentials:
            raise AccessTokenRequired()

        token = creds.credentials
        token_data = decode_token(token)

        # Vérifier si le token est dans la blacklist Redis
        try:
            if await is_jti_in_blocklist(token_data["jti"]):
                logger.warning(f"Token blacklisted: {token_data['jti']}")
                raise RevokedToken()
        except RevokedToken:
            raise  # Re-lever l'exception de token révoqué
        except Exception as e:
            logger.warning(f"Redis error during token blacklist check: {e}")
            # On continue si Redis indisponible

        # Vérifier le type de token spécifique
        self.verify_token_data(token_data)
        return token_data

    def verify_token_data(self, token_data: dict) -> None:
        raise NotImplementedError("Please implement this method in subclass.")


class AccessTokenBearer(AccessToken):
    """Validateur pour les tokens d'accès"""

    def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh", False) or token_data.get("type") == "refresh":
            raise RefreshTokenRequired()


class RefreshTokenBearer(AccessToken):
    """Validateur pour les tokens de rafraîchissement"""

    def verify_token_data(self, token_data: dict) -> None:
        # Corriger la logique : un refresh token doit avoir refresh=True OU type="refresh"
        if not (token_data.get("refresh", False) or token_data.get("type") == "refresh"):
            raise AccessTokenRequired()


# python
async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(AccessTokenBearer())
) -> UtilisateurRead:
    try:
        user_data = token_details.get("user")
        if isinstance(user_data, dict) and "user" in user_data:
            user_data = user_data["user"]
        if not user_data or not isinstance(user_data, dict):
            raise InvalidToken()
        user_email = (
            user_data.get("email")
            or user_data.get("username")
            or token_details.get("sub")
        )
        if not user_email:
            logger.error(f"No email found in token data: {user_data}")
            raise InvalidToken()
        # Charger l'utilisateur avec ses relations
        user = await users_service.get_user_by_email(user_email, session=session)
        if not user:
            logger.warning(f"User not found for email: {user_email}")
            raise UserNotFound()
        if not getattr(user, 'is_verified', False):
            logger.warning(f"User {user_email} attempted to access with unverified email")
            raise EmailNotVerified()
        # Enrichir avec les champs du profil lié
        data = UtilisateurRead.model_validate(user, from_attributes=True)
        if user.status == "Etudiant" and user.etudiant:
            data.niveau_technique = user.etudiant.niveau_technique
            data.competences = user.etudiant.competences
            data.objectifs_apprentissage = user.etudiant.objectifs_apprentissage
            data.motivation = user.etudiant.motivation
            data.niveau_energie = user.etudiant.niveau_energie
        elif user.status == "Professeur" and user.professeur:
            data.niveau_experience = user.professeur.niveau_experience
            data.specialites = user.professeur.specialites
            data.motivation_principale = user.professeur.motivation_principale
            data.niveau_technologique = user.professeur.niveau_technologique
        return data
    except (UserNotFound, InvalidToken, RevokedToken, EmailNotVerified):
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise InvalidToken()


async def get_current_user_id(
    token_details: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    """
    Récupère uniquement l'ID de l'utilisateur depuis le token.
    Version allégée de get_current_user pour les endpoints qui n'ont besoin que de l'ID.
    """
    from uuid import UUID
    try:
        user_data = token_details.get("user")
        if isinstance(user_data, dict) and "user" in user_data:
            user_data = user_data["user"]
        if not user_data or not isinstance(user_data, dict):
            raise InvalidToken()

        # Essayer de récupérer l'ID directement
        user_id = user_data.get("id")
        if user_id:
            return UUID(str(user_id))

        # Fallback: récupérer via l'email
        user_email = user_data.get("email") or user_data.get("username") or token_details.get("sub")
        if not user_email:
            raise InvalidToken()

        # Requête DB pour récupérer l'ID
        user = await users_service.get_user_by_email(user_email, session=session)
        if not user:
            raise UserNotFound()

        return user.id
    except Exception as e:
        logger.error(f"Error getting current user ID: {e}")
        raise InvalidToken()
        data = UtilisateurRead.model_validate(user, from_attributes=True)
        if user.status == "Etudiant" and user.etudiant:
            data.niveau_technique = user.etudiant.niveau_technique
            data.competences = user.etudiant.competences
            data.objectifs_apprentissage = user.etudiant.objectifs_apprentissage
            data.motivation = user.etudiant.motivation
            data.niveau_energie = user.etudiant.niveau_energie
        elif user.status == "Professeur" and user.professeur:
            data.niveau_experience = user.professeur.niveau_experience
            data.specialites = user.professeur.specialites
            data.motivation_principale = user.professeur.motivation_principale
            data.niveau_technologique = user.professeur.niveau_technologique
        return data
    except (UserNotFound, InvalidToken, RevokedToken, EmailNotVerified):
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue dans get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur pendant la récupération des informations utilisateur"
        )




class RoleChecker:
    """Vérificateur de rôles avec email vérifié par défaut"""

    def __init__(self, allowed_roles: List[str], require_verified_email: bool = True):
        if not allowed_roles:
            raise ValueError("Au moins un rôle doit être spécifié")
        self.allowed_roles = allowed_roles
        self.require_verified_email = require_verified_email

    async def __call__(self,
                      current_user: UtilisateurRead = Depends(get_current_user)
                      ) -> UtilisateurRead:
        # get_current_user vérifie déjà l'email automatiquement
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if current_user.status not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )

        return current_user



# Helpers
def require_admin() -> RoleChecker:
    return RoleChecker(["admin"])


def require_professor() -> RoleChecker:
    return RoleChecker(["Professeur"])


def require_student() -> RoleChecker:
    return RoleChecker(["Etudiant"])


def require_professor_or_admin() -> RoleChecker:
    return RoleChecker(["Professeur", "admin"])


def require_any_user() -> RoleChecker:
    return RoleChecker(["Professeur", "Etudiant", "admin"])
