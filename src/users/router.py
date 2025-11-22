from datetime import timedelta, datetime, timezone
from typing import List
from fastapi import APIRouter, status, Depends, HTTPException,BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi.responses import JSONResponse
import logging

from src.db.main import get_session
from src.db.redis import (
    get_all_users_cache,
    set_all_users_cache,
    set_user_cache,
    invalidate_all_users_cache,
    add_jti_to_blocklist
)
from .models import StatutUtilisateur
from .utils import create_access_token
from src.users.schema import (
    UtilisateurRead,
    UtilisateurCreateBase,
    UserLogin,
    EmailModel,
    PasswordResetModel,
    PasswordResetConfirm
)
from src.users.services import UserService
from src.users.utils import verify_password_hash ,generate_password_hash
from src.users.dependencies import AccessTokenBearer
from .dependencies import RefreshTokenBearer
from .dependencies import get_current_user, RoleChecker
from ..celery_tasks import send_email
from ..error import (
    InvalidToken,
    UserNotFound,
    UserAlreadyExists,
    ExpiredToken,
    AccessTokenRequired
)
from src.config import Config

# Logger
logger = logging.getLogger("user_router")
logger.setLevel(logging.INFO)


# Configuration
roles = [role.value for role in StatutUtilisateur]
role = ["admin", "user"]
role_checker = RoleChecker(role)

access_token = AccessTokenBearer()
refresh_token = RefreshTokenBearer()

user_router = APIRouter()
user_service = UserService()
REFRESH_TOKEN_EXPIRATION = 2  # en jours

@user_router.post("/send_mail")
async def send_mail(emailmodel:EmailModel):
    email = emailmodel.mails
    subject = "welcome"
    body = "<h1>Welcome to my app</h1>"
    send_email.delay(email,subject,body)
    return JSONResponse(
        "message sent",
        status_code=status.HTTP_201_CREATED
    )


# Vérification d'email avec token sécurisé
@user_router.get("/verify/{token}")
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    """
    Vérifie l'email d'un utilisateur avec un token sécurisé.
    Le token expire après 24 heures.
    """
    try:
        from src.users.tokens import TokenService
        from src.users.email_templates import get_welcome_email_template

        # Vérifier et valider le token
        token_obj = await TokenService.verify_token(
            token=token,
            token_type="email_verification",
            session=session
        )

        if not token_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou expiré. Veuillez demander un nouveau lien de vérification."
            )

        # Récupérer l'utilisateur
        user = await user_service.get_user(token_obj.user_id, session)
        if not user:
            raise UserNotFound()

        # Vérifier si déjà vérifié
        if user.is_verified:
            return JSONResponse(
                content={"message": "Votre compte est déjà vérifié. Vous pouvez vous connecter."},
                status_code=status.HTTP_200_OK
            )

        # Vérifier le compte
        await user_service.update_user(user, {'is_verified': True}, session)

        # Envoyer un email de bienvenue
        welcome_html = get_welcome_email_template(username=user.username)
        send_email.delay(
            [user.email],
            "🎉 Bienvenue sur AI4D !",
            welcome_html
        )

        logger.info(f"User verified successfully: {user.id}")

        return JSONResponse(
            content={
                "message": "✅ Compte vérifié avec succès ! Vous pouvez maintenant vous connecter.",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "is_verified": True
                }
            },
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except UserNotFound:
        raise
    except Exception as e:
        logger.error(f"Error during email verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la vérification"
        )




# --- GET all users ---
@user_router.get("/", response_model=List[UtilisateurRead])
async def get_all_users(
        session: AsyncSession = Depends(get_session),
        user_details=Depends(AccessTokenBearer()),
):
    try:
        if not user_details:
            raise AccessTokenRequired()

        jti = user_details.get('jti')
        if not jti:
            raise InvalidToken()
        # Tentative de récupération depuis le cache
        try:
            cached = await get_all_users_cache()
            if cached:
                logger.info("Cache hit for all users")
                return [UtilisateurRead.model_validate(u) for u in cached]
        except Exception as e:
            logger.warning(f"Redis unavailable for all users cache: {e}")

        # Récupération depuis la base de données
        users_result = await user_service.get_all_users(session)
        if not users_result:
            return []

        users_data = [UtilisateurRead.model_validate(u, from_attributes=True) for u in users_result]

        # Mise à jour du cache
        try:
            await set_all_users_cache(users_data)
        except Exception as e:
            logger.warning(f"Redis unavailable, cannot cache all users: {e}")

        return users_data

    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching users"
        )


# --- CREATE user ---
@user_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user(
        bgtask: BackgroundTasks,
        data: UtilisateurCreateBase,
        session: AsyncSession = Depends(get_session),
):
    """
    Inscription d'un nouvel utilisateur avec envoi d'email de vérification.

    ⚠️ IMPORTANT: Cette route crée UNIQUEMENT l'utilisateur de base (compte).
    Le profil détaillé (Etudiant/Professeur) et le profil MongoDB seront créés
    APRÈS le questionnaire initial via POST /api/profile/v1/analyze_quiz.

    Flux d'inscription:
    1. POST /signup → Crée l'utilisateur de base + envoi email de vérification
    2. GET /verify/{token} → Vérifie l'email
    3. POST /login → Connexion
    4. Frontend vérifie hasProfile() → false → Redirige vers /questionnaire
    5. POST /analyze_quiz → Crée le profil MongoDB + profil Etudiant/Professeur
    6. hasProfile() → true → Dashboard accessible

    Le token de vérification expire après 24 heures.
    """
    try:
        from src.users.tokens import TokenService
        from src.users.email_templates import get_verification_email_template

        if not data.email or not data.motDePasseHash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )

        # Normaliser l'email dès le début
        normalized_email = str(data.email).strip().lower()

        existing_user = await user_service.get_user_by_email(normalized_email, session)
        if existing_user:
            raise UserAlreadyExists()

        # Revalider via le schéma pour conserver EmailStr
        data = UtilisateurCreateBase(**{**data.model_dump(), "email": normalized_email})

        # ✅ CHANGEMENT: create_user crée maintenant UNIQUEMENT l'utilisateur de base
        # Le profil Etudiant/Professeur sera créé après le questionnaire
        user = await user_service.create_user(session, data)
        user_data = UtilisateurRead.model_validate(user, from_attributes=True)

        # Créer un token de vérification sécurisé avec expiration (24h)
        verification_token = await TokenService.create_verification_token(
            user_id=str(user.id),
            session=session,
            token_type="email_verification",
            expiry_hours=24
        )

        # Créer le lien de vérification
        verification_link = f"http://{Config.DOMAIN}/api/auth/v1/verify/{verification_token.token}"

        # Générer l'email HTML professionnel
        html_message = get_verification_email_template(
            username=user.username,
            verification_link=verification_link
        )

        email = [normalized_email]
        subject = "🚀 Vérifiez votre compte AI4D"
        send_email.delay(email, subject, html_message)

        try:
            await set_user_cache(user_data)
            await invalidate_all_users_cache()
        except Exception as e:
            logger.warning(f"Redis unavailable during user cache update: {e}")

        logger.info(f"User created with verification token: {user_data.id}")
        return {
            "message": "Compte créé avec succès ! Vérifiez votre email pour activer votre compte (lien valable 24h).",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_verified": user.is_verified
            }
        }

    except UserAlreadyExists:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating user"
        )


# --- LOGIN user ---
@user_router.post("/login")
async def login_user(login: UserLogin, session: AsyncSession = Depends(get_session)):
    """
    Connexion d'un utilisateur. Le compte doit être vérifié pour se connecter.
    """
    try:
        # Validation des données d'entrée
        if not login.email or not login.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )

        email = str(login.email)
        password = login.password

        # Recherche de l'utilisateur
        user = await user_service.get_user_by_email(email, session)
        if not user:
            raise UserNotFound()

        # Vérification du mot de passe
        if not verify_password_hash(password, user.motDePasseHash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # ✅ NOUVEAU: Vérifier que le compte est vérifié
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte non vérifié. Veuillez vérifier votre email avant de vous connecter."
            )

        # Création des tokens
        payload = {
            'user': {
                'email': str(user.email),
                'id': str(user.id),
                'username': str(user.username),
                'status': str(user.status),
            }
        }

        try:
            access_token_value = create_access_token(data=payload)
            refresh_token_value = create_access_token(
                data=payload,
                expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRATION),
                refresh=True
            )
        except Exception as e:
            logger.error(f"Error creating tokens: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating authentication tokens"
            )

        logger.info(f"User logged in: {user.id}")
        return JSONResponse(
            content={
                "message": "Successfully logged in",
                "access_token": access_token_value,
                "refresh_token": refresh_token_value,
                "user": {
                    "id": str(user.id),
                    "username": str(user.username),
                    "email": str(user.email),
                    "is_verified": user.is_verified
                }
            }
        )

    except UserNotFound:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


# --- REFRESH token ---
@user_router.get("/refresh_token")
async def get_new_access_token(token_detail: dict = Depends(RefreshTokenBearer())):
    try:
        if not token_detail:
            raise InvalidToken()

        expire_timestamp = token_detail.get('exp')
        if not expire_timestamp:
            raise InvalidToken()

        now = datetime.now(timezone.utc).timestamp()
        if expire_timestamp <= now:
            raise ExpiredToken()

        user_data = token_detail.get("user")
        if not user_data:
            raise InvalidToken()

        try:
            new_access_token = create_access_token(data={"user": user_data})
        except Exception as e:
            logger.error(f"Error creating new access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating new access token"
            )

        logger.info(f"Access token refreshed for user: {user_data.get('id', 'unknown')}")
        return JSONResponse(content={"access_token": new_access_token})

    except (InvalidToken, ExpiredToken):
        raise  # Re-raise custom exceptions
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while refreshing token"
        )


# --- GET current user ---
@user_router.get("/me", response_model=UtilisateurRead)
async def get_current_user_info(user_details: dict = Depends(get_current_user)):
    try:
        if not user_details:
            raise AccessTokenRequired()

        return user_details

    except AccessTokenRequired:
        raise  # Re-raise custom exceptions
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting user information"
        )


# --- LOGOUT user ---
@user_router.get("/logout")
async def logout(token_detail: dict = Depends(AccessTokenBearer())):
    if not token_detail:
        raise AccessTokenRequired()

    jti = token_detail.get("jti")
    if not jti:
        raise InvalidToken()

    try:
        # NX=True => n'ajoute pas si déjà présent
        added = await add_jti_to_blocklist(jti=jti)

        if added:
            logger.info(f"Token JTI {jti} added to blocklist")
            already_blacklisted = False
        else:
            logger.info(f"Token JTI {jti} already in blocklist")
            already_blacklisted = True

    except Exception as e:
        logger.error(f"Redis error adding token {jti} to blocklist: {str(e)}")
        # On continue quand même → logout ne doit pas échouer
        already_blacklisted = None

    logger.info(f"User logged out: {token_detail.get('user', {}).get('id', 'unknown')}")
    return JSONResponse(
        content={
            "message": "Successfully logged out",
            "already_blacklisted": already_blacklisted
        },
        status_code=status.HTTP_200_OK,
    )






# --- PASSWORD RESET REQUEST ---
@user_router.post("/password_reset_request")
async def password_reset_request(
    email_model: PasswordResetModel,
    session: AsyncSession = Depends(get_session)
):
    """
    Demande de réinitialisation de mot de passe.
    Le token expire après 1 heure pour la sécurité.
    """
    try:
        from src.users.tokens import TokenService
        from src.users.email_templates import get_password_reset_email_template

        email = str(email_model.email).strip().lower()

        # Vérifier que l'utilisateur existe
        user = await user_service.get_user_by_email(email, session)

        # SÉCURITÉ: Ne pas révéler si l'email existe ou non
        # Toujours retourner le même message
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return JSONResponse(
                content={
                    "message": "Si cet email existe dans notre système, vous recevrez un lien de réinitialisation."
                },
                status_code=status.HTTP_200_OK
            )

        # Créer un token de reset avec expiration d'1 heure
        reset_token = await TokenService.create_verification_token(
            user_id=str(user.id),
            session=session,
            token_type="password_reset",
            expiry_hours=1  # 1 heure pour plus de sécurité
        )

        # Créer le lien de reset
        reset_link = f"http://{Config.DOMAIN}/api/auth/v1/password_reset_confirm/{reset_token.token}"

        # Générer l'email HTML professionnel
        html_message = get_password_reset_email_template(
            username=user.username,
            reset_link=reset_link
        )

        send_email.delay(
            [email],
            "🔐 Réinitialisation de votre mot de passe AI4D",
            html_message
        )

        logger.info(f"Password reset requested for user: {user.id}")

        return JSONResponse(
            content={
                "message": "Si cet email existe dans notre système, vous recevrez un lien de réinitialisation (valable 1 heure)."
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error in password reset request: {str(e)}")
        # SÉCURITÉ: Ne pas révéler les erreurs internes
        return JSONResponse(
            content={
                "message": "Si cet email existe dans notre système, vous recevrez un lien de réinitialisation."
            },
            status_code=status.HTTP_200_OK
        )


# --- PASSWORD RESET CONFIRM ---
@user_router.post("/password_reset_confirm/{token}")
async def password_reset_confirm(
    token: str,
    passwords: PasswordResetConfirm,
    session: AsyncSession = Depends(get_session)
):
    """
    Confirme la réinitialisation du mot de passe avec un token sécurisé.
    Le token expire après 1 heure.
    """
    try:
        from src.users.tokens import TokenService

        new_password = passwords.new_password
        confirm_new_password = passwords.confirm_new_password

        # Vérifier que les mots de passe correspondent
        if new_password != confirm_new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Les mots de passe ne correspondent pas"
            )

        # Vérifier la force du mot de passe (minimum 8 caractères)
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe doit contenir au moins 8 caractères"
            )

        # Vérifier et valider le token
        token_obj = await TokenService.verify_token(
            token=token,
            token_type="password_reset",
            session=session
        )

        if not token_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token invalide ou expiré. Veuillez faire une nouvelle demande de réinitialisation."
            )

        # Récupérer l'utilisateur
        user = await user_service.get_user(token_obj.user_id, session)
        if not user:
            raise UserNotFound()

        # Mettre à jour le mot de passe
        password_hash = generate_password_hash(new_password)
        await user_service.update_user(user, {'motDePasseHash': password_hash}, session)

        logger.info(f"Password reset successfully for user: {user.id}")

        return JSONResponse(
            content={
                "message": "✅ Mot de passe réinitialisé avec succès ! Vous pouvez maintenant vous connecter."
            },
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        raise
    except UserNotFound:
        raise
    except Exception as e:
        logger.error(f"Error in password reset confirm: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la réinitialisation du mot de passe"
        )


# --- RESEND VERIFICATION EMAIL ---
@user_router.post("/resend_verification")
async def resend_verification_email(
    email_model: EmailModel,
    session: AsyncSession = Depends(get_session)
):
    """
    Renvoie un email de vérification à un utilisateur.
    Le nouveau token expire après 24 heures.
    """
    try:
        from src.users.tokens import TokenService
        from src.users.email_templates import get_verification_email_template

        email = str(email_model.mails[0]).strip().lower() if isinstance(email_model.mails, list) else str(email_model.mails).strip().lower()

        # Rechercher l'utilisateur
        user = await user_service.get_user_by_email(email, session)

        if not user:
            # SÉCURITÉ: Ne pas révéler si l'email existe
            return JSONResponse(
                content={
                    "message": "Si cet email existe et n'est pas encore vérifié, un nouveau lien vous sera envoyé."
                },
                status_code=status.HTTP_200_OK
            )

        # Vérifier si déjà vérifié
        if user.is_verified:
            return JSONResponse(
                content={
                    "message": "Ce compte est déjà vérifié. Vous pouvez vous connecter."
                },
                status_code=status.HTTP_200_OK
            )

        # Créer un nouveau token de vérification
        verification_token = await TokenService.create_verification_token(
            user_id=str(user.id),
            session=session,
            token_type="email_verification",
            expiry_hours=24
        )

        # Créer le lien de vérification
        verification_link = f"http://{Config.DOMAIN}/api/auth/v1/verify/{verification_token.token}"

        # Générer l'email HTML
        html_message = get_verification_email_template(
            username=user.username,
            verification_link=verification_link
        )

        send_email.delay(
            [email],
            "🚀 Vérifiez votre compte AI4D",
            html_message
        )

        logger.info(f"Verification email resent to user: {user.id}")

        return JSONResponse(
            content={
                "message": "Un nouveau lien de vérification vous a été envoyé par email (valable 24h)."
            },
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error resending verification email: {str(e)}")
        return JSONResponse(
            content={
                "message": "Si cet email existe et n'est pas encore vérifié, un nouveau lien vous sera envoyé."
            },
            status_code=status.HTTP_200_OK
        )
