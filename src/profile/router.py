from datetime import datetime
import logging
from fastapi import Request
from src.users.utils import decode_token
import jwt
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from src.error import ProfileNotFound
from src.profile.schema import ProfilResponse, ProfilCreate, ProfilUpdate, XPRequest, BadgeRequest, ActivityRequest
from src.profile.services import profile_service
from src.users.dependencies import get_current_user
from src.users.models import Utilisateur
from src.users.schema import UtilisateurRead  # pour typing facultatif


# Import des fonctions Redis pour les profils
from src.db.profile_redis import (
    get_profile_cache,
    set_profile_cache,
    get_leaderboard_cache,
    set_leaderboard_cache,
    invalidate_leaderboard_cache,
    get_profile_stats_cache,
    set_profile_stats_cache,
    get_activities_cache,
    set_activities_cache,
    invalidate_user_related_caches
)
from ..celery_tasks import  generate_profile_question_task
# Ajout import de la tâche d'analyse
from ..celery_tasks import profile_analysis_task


router = APIRouter()
logger = logging.getLogger("profile_router")


@router.post("/", response_model=ProfilResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
        profile_data: ProfilCreate,
        current_user: Utilisateur = Depends(get_current_user)
):
    """Créer le profil de l'utilisateur connecté"""

    # Assigner automatiquement l'ID de l'utilisateur connecté
    profile_data.utilisateur_id = current_user.id

    try:
        profile = await profile_service.create_profile(profile_data)

        # Mettre en cache le nouveau profil
        try:
            profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile.__dict__
            await set_profile_cache(current_user.id, profile_dict)
            # Invalider le leaderboard car nouveau profil
            await invalidate_leaderboard_cache()
        except Exception as e:
            logger.warning(f"Redis caching failed after profile creation: {e}")

        return profile

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating profile"
        )


@router.get("/", response_model=ProfilResponse)
async def get_my_profile(
        current_user: Utilisateur = Depends(get_current_user)
):
    """
    Récupérer le profil de l'utilisateur connecté.

    ⚠️ IMPORTANT: Cette route ne crée PLUS automatiquement le profil.
    Le profil est créé UNIQUEMENT après le questionnaire initial.

    Si le profil n'existe pas → 404
    Le frontend doit rediriger vers /questionnaire dans ce cas.
    """

    # Tentative de récupération depuis le cache
    try:
        cached_profile = await get_profile_cache(current_user.id)
        if cached_profile:
            logger.info(f"Profile cache hit for user {current_user.id}")
            return ProfilResponse.model_validate(cached_profile)
    except Exception as e:
        logger.warning(f"Redis unavailable for profile cache: {e}")

    # Récupération depuis la base de données
    profile = await profile_service.get_profile_by_user_id(current_user.id)

    if not profile:
        # ✅ CHANGEMENT: Ne plus créer automatiquement le profil
        # Le profil sera créé après le questionnaire initial
        logger.info(f"Profile not found for user {current_user.id} - questionnaire required")
        raise ProfileNotFound()

    # Mettre en cache le profil récupéré
    try:
        profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile.__dict__
        await set_profile_cache(current_user.id, profile_dict)
    except Exception as e:
        logger.warning(f"Redis caching failed after profile retrieval: {e}")

    return profile


# Alias pour /me qui est souvent utilisé par les frontends
@router.get("/me", response_model=ProfilResponse)
async def get_profile_me(current_user: Utilisateur = Depends(get_current_user)):
    """Alias de GET / pour récupérer le profil de l'utilisateur connecté"""
    return await get_my_profile(current_user)


@router.put("/", response_model=ProfilResponse)
async def update_profile(
        update_data: ProfilUpdate,
        current_user: Utilisateur = Depends(get_current_user)
):
    """Mettre à jour le profil de l'utilisateur connecté"""

    profile = await profile_service.update_profile(current_user.id, update_data)
    if not profile:
        raise ProfileNotFound()

    # Invalider et mettre à jour le cache
    try:
        await invalidate_user_related_caches(current_user.id)  # Invalide tous les caches liés à l'utilisateur
        profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile.__dict__
        await set_profile_cache(current_user.id, profile_dict)
    except Exception as e:
        logger.warning(f"Redis cache update failed after profile update: {e}")

    return profile


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
        current_user: Utilisateur = Depends(get_current_user)
):
    """Supprimer le profil de l'utilisateur connecté"""

    success = await profile_service.delete_profile(current_user.id)
    if not success:
        raise ProfileNotFound()

    # Invalider tous les caches liés à l'utilisateur
    try:
        await invalidate_user_related_caches(current_user.id)
    except Exception as e:
        logger.warning(f"Redis cache invalidation failed after profile deletion: {e}")


@router.post("/xp")
async def add_xp(
        xp_request: XPRequest,
        current_user: Utilisateur = Depends(get_current_user)
):
    """Ajouter de l'XP au profil de l'utilisateur connecté"""

    if xp_request.xp_points <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XP points must be positive"
        )

    profile = await profile_service.add_xp(current_user.id, xp_request.xp_points)
    if not profile:
        raise ProfileNotFound()

    # Invalider les caches (profil, stats, leaderboard)
    try:
        await invalidate_user_related_caches(current_user.id)
        # Mettre à jour le cache du profil
        profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile.__dict__
        await set_profile_cache(current_user.id, profile_dict)
    except Exception as e:
        logger.warning(f"Redis cache update failed after XP addition: {e}")

    return {
        "message": f"Added {xp_request.xp_points} XP",
        "new_xp": profile.xp,
        "level": profile.niveau
    }


@router.get("/stats")
async def get_profile_stats(
        current_user: Utilisateur = Depends(get_current_user)
):
    """Obtenir les statistiques du profil de l'utilisateur connecté"""

    # Vérifier le cache des stats
    try:
        cached_stats = await get_profile_stats_cache(current_user.id)
        if cached_stats:
            logger.info(f"Profile stats cache hit for user {current_user.id}")
            return cached_stats
    except Exception as e:
        logger.warning(f"Redis unavailable for stats cache: {e}")

    # Récupérer depuis le service
    stats = await profile_service.get_profile_stats(current_user.id)
    if not stats:
        raise ProfileNotFound()

    # Mettre en cache les stats
    try:
        await set_profile_stats_cache(current_user.id, stats)
    except Exception as e:
        logger.warning(f"Redis caching failed for profile stats: {e}")

    return stats


@router.get("/recommendations")
async def get_recommendations(current_user: Utilisateur = Depends(get_current_user)):
    """
    Récupère les recommandations personnalisées pour l'utilisateur.

    Les recommandations sont basées sur :
    - L'analyse du questionnaire initial (questions ouvertes)
    - Les performances aux quiz
    - Les forces et faiblesses identifiées
    """
    logger.info(f"[RECOMMENDATIONS] Fetching recommendations for user {current_user.id}")

    profile = await profile_service.get_profile_by_user_id(current_user.id)

    if not profile:
        logger.error(f"[RECOMMENDATIONS] Profile not found for user {current_user.id}")
        raise ProfileNotFound()

    logger.info(f"[RECOMMENDATIONS] Profile found: questionnaire_complete={profile.questionnaire_initial_complete}, recommendations_count={len(profile.recommandations or [])}")

    recommendations = profile.recommandations or []

    # Enrichir avec des informations contextuelles
    result = {
        "recommendations": recommendations,
        "total": len(recommendations),
        "questionnaire_complete": profile.questionnaire_initial_complete,
        "niveau": profile.niveau,
        "competences": profile.competences,
        "objectifs": profile.objectifs,
    }

    # Si le questionnaire initial est fait, ajouter l'analyse des questions ouvertes
    if profile.questionnaire_initial_complete and profile.analyse_questions_ouvertes:
        result["analyse_questions_ouvertes"] = {
            "niveau_reel": profile.analyse_questions_ouvertes.get("evaluation_detaillee", {}).get("niveau_reel_estime", "non_determine"),
            "comprehension_profonde": profile.analyse_questions_ouvertes.get("evaluation_detaillee", {}).get("comprehension_profonde", "non_evaluee"),
            "capacite_explication": profile.analyse_questions_ouvertes.get("evaluation_detaillee", {}).get("capacite_explication", "non_evaluee"),
        }

    logger.info(f"[RECOMMENDATIONS] Returning {len(recommendations)} recommendations")
    return result


@router.get("/leaderboard")
async def get_leaderboard(
        current_user: Utilisateur = Depends(get_current_user),
        limit: int = Query(10, ge=1, le=100, description="Nombre de profils à retourner")
):
    """
    Obtenir le classement des utilisateurs par XP (authentification requise)

    SÉCURITÉ: Affiche username au lieu de UUID pour protéger la vie privée
    """

    # Vérifier le cache du leaderboard
    try:
        cached_leaderboard = await get_leaderboard_cache()
        if cached_leaderboard:
            logger.info("Leaderboard cache hit")
            # Appliquer la limite sur les données cachées
            limited_data = cached_leaderboard[:limit]

            # Marquer l'utilisateur connecté
            for entry in limited_data:
                entry["is_me"] = (entry.get("username") == current_user.username)

            return {
                "leaderboard": limited_data,
                "total_results": len(limited_data)
            }
    except Exception as e:
        logger.warning(f"Redis unavailable for leaderboard cache: {e}")

    try:
        leaderboard = await profile_service.get_leaderboard(limit)

        # Marquer l'utilisateur connecté
        for entry in leaderboard:
            entry["is_me"] = (entry.get("username") == current_user.username)

        # Mettre en cache le leaderboard complet (sans le flag is_me)
        try:
            full_leaderboard = await profile_service.get_leaderboard(100)
            await set_leaderboard_cache(full_leaderboard)
        except Exception as e:
            logger.warning(f"Redis caching failed for leaderboard: {e}")

        return {
            "leaderboard": leaderboard,
            "total_results": len(leaderboard)
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get leaderboard"
        )


@router.get("/activities")
async def get_activity_history(
        current_user: Utilisateur = Depends(get_current_user),
        limit: int = Query(50, ge=1, le=200, description="Nombre d'activités à retourner")
):
    """Obtenir l'historique des activités de l'utilisateur connecté"""

    # Vérifier le cache des activités
    try:
        cached_activities = await get_activities_cache(current_user.id)
        if cached_activities:
            logger.info(f"Activities cache hit for user {current_user.id}")
            limited_activities = cached_activities[:limit]
            return {
                "activities": limited_activities,
                "total_activities": len(cached_activities)
            }
    except Exception as e:
        logger.warning(f"Redis unavailable for activities cache: {e}")

    # Récupérer depuis la base de données
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Retourner les dernières activités triées par timestamp
    activities = sorted(
        profile.historique_activites,
        key=lambda x: x.get("timestamp", datetime.min),
        reverse=True
    )

    # Mettre en cache toutes les activités
    try:
        await set_activities_cache(current_user.id, activities)
    except Exception as e:
        logger.warning(f"Redis caching failed for activities: {e}")

    limited_activities = activities[:limit]
    return {
        "activities": limited_activities,
        "total_activities": len(activities)
    }


# Endpoints avec invalidation de cache pour les actions qui modifient les données
@router.post("/badges")
async def add_badge(
        badge_request: BadgeRequest,
        current_user: Utilisateur = Depends(get_current_user)
):
    """Ajouter un badge au profil de l'utilisateur connecté"""

    profile = await profile_service.add_badge(current_user.id, badge_request.badge)
    if not profile:
        raise ProfileNotFound()

    # Invalider et mettre à jour le cache
    try:
        await invalidate_user_related_caches(current_user.id)
        profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile.__dict__
        await set_profile_cache(current_user.id, profile_dict)
    except Exception as e:
        logger.warning(f"Redis cache update failed after badge addition: {e}")

    return {
        "message": f"Badge '{badge_request.badge}' added",
        "total_badges": len(profile.badges),
        "badges": profile.badges
    }


@router.post("/activities")
async def complete_activity(
        activity_request: ActivityRequest,
        current_user: Utilisateur = Depends(get_current_user)
):
    """Enregistrer une activité terminée et optionnellement ajouter de l'XP"""

    profile = await profile_service.complete_activity(
        user_id=current_user.id,
        activity_type=activity_request.activity_type,
        xp_reward=activity_request.xp_reward
    )

    if not profile:
        raise ProfileNotFound()

    # Invalider tous les caches car activité + potentiel XP
    try:
        await invalidate_user_related_caches(current_user.id)
        profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile.__dict__
        await set_profile_cache(current_user.id, profile_dict)
    except Exception as e:
        logger.warning(f"Redis cache update failed after activity completion: {e}")

    return {
        "message": f"Activity '{activity_request.activity_type}' completed",
        "xp_earned": activity_request.xp_reward,
        "total_xp": profile.xp,
        "level": profile.niveau
    }



@router.get("/debug-token-detailed")
async def debug_token_detailed(request: Request):
    """Diagnostic détaillé du token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return {"error": "Aucun en-tête d'autorisation"}

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {"error": "Format d'autorisation invalide"}

    token = parts[1]
    try:
        # Décoder sans validation pour voir le contenu brut
        decoded_raw = jwt.decode(token, options={"verify_signature": False})

        # Décoder avec validation complète
        try:
            decoded = decode_token(token)
            status = "valide"
        except Exception as e:
            decoded = None
            status = f"invalide: {str(e)}"

        return {
            "token_status": status,
            "raw_payload": decoded_raw,
            "structure": {
                "has_user_field": "user" in decoded_raw if decoded_raw else False,
                "top_level_keys": list(decoded_raw.keys()) if decoded_raw else []
            },
            "validated_token": decoded
        }
    except Exception as e:
        return {"error": f"Erreur de décodage: {str(e)}"}


@router.get("/healthcheck")
async def health_check():
    """Vérification de l'API sans authentification"""
    return {"status": "ok", "message": "API de profil fonctionnelle"}


# Génération de question personnalisée - MAINTENANT PAR DOMAINE
try:
    from src.ai_agents.profiler.questionnaires_par_domaine import (
        get_questionnaire_for_domain,
        get_available_domains
    )
except Exception:
    get_questionnaire_for_domain = None
    get_available_domains = None


@router.get("/domains")
async def get_available_professions():
    """Retourne les domaines professionnels disponibles"""
    if not get_available_domains:
        return {
            "domains": [
                "Droit & Justice",
                "Marketing & Communication",
                "Santé & Médecine",
                "Finance & Comptabilité",
                "Informatique & Développement",
                "Éducation & Formation"
            ]
        }
    return {"domains": get_available_domains()}


@router.get("/initial_questionnaire")
async def get_initial_questionnaire(
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Retourne les questions du questionnaire initial adapté au domaine de l'utilisateur.

    Ce questionnaire:
    - Est fait UNE SEULE FOIS pour créer le profil initial
    - Est adapté au domaine d'études (Informatique, Droit, Marketing, etc.)
    - Contient des questions de choix multiple et 1-2 questions ouvertes maximum
    - Ne contient PAS de vraies/faux
    """
    try:
        from src.ai_agents.profiler.questionnaires_domaines import DomainQuestionnaireGenerator

        # Vérifier si l'utilisateur a déjà un profil complété
        profile = await profile_service.get_profile_by_user_id(current_user.id)
        if profile and profile.questionnaire_initial_complete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous avez déjà complété le questionnaire initial. Un profil a été créé pour vous."
            )

        # Extraire le domaine de l'utilisateur
        domaine = "Général"
        if hasattr(current_user, 'etudiant') and current_user.etudiant:
            domaine = str(current_user.etudiant.domaine)
        elif hasattr(current_user, 'professeur') and current_user.professeur:
            domaine = str(current_user.professeur.domaine)

        # Récupérer les questions adaptées au domaine
        questions = DomainQuestionnaireGenerator.get_questions_for_domain(domaine)

        return {
            "domaine": domaine,
            "questions": questions,
            "total_questions": len(questions),
            "instructions": f"Questionnaire de profilage adapté au domaine: {domaine}",
            "note": "Ce questionnaire crée votre profil et ne peut être fait qu'une seule fois"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting initial questionnaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du chargement du questionnaire"
        )


@router.get("/questionnaire")
async def get_questionnaire(
    domain: str = None,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Retourne le questionnaire adapté au domaine professionnel de l'utilisateur.
    Les questions sont VARIÉES et MÉLANGÉES à chaque appel pour éviter la répétition.

    Si domain n'est pas fourni, utilise le profil de l'utilisateur pour déterminer le domaine.
    Si pas de profil, utilise Informatique & Développement par défaut.
    """
    try:
        # Déterminer le domaine
        if not domain:
            # Chercher dans le profil si le domaine est connu
            profile = await profile_service.get_profile_by_user_id(current_user.id)
            if profile and hasattr(profile, 'domaine_application'):
                domain = profile.domaine_application
            else:
                # Défaut : Informatique
                domain = "Informatique & Développement"

        # 🎲 Récupérer des questions VARIÉES et MÉLANGÉES au lieu des mêmes
        from src.ai_agents.profiler.questionnaires_par_domaine import get_shuffled_questions
        questions = get_shuffled_questions(domain, num_questions=5)

        return {
            "domain": domain,
            "description": f"Questions variées pour {domain}",
            "questions": questions,
            "total_questions": len(questions)
        }

    except Exception as e:
        logger.error(f"Error getting questionnaire: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du questionnaire")


@router.get("/question")
async def get_profile_question(current_user: Utilisateur = Depends(get_current_user)):
    try:
        u = UtilisateurRead.model_validate(current_user, from_attributes=True)
        user_dict = u.model_dump()  # Conversion en dict
        task = generate_profile_question_task.delay(user_dict)
        return {"task_id": task.id}
    except Exception as e:
        logger.warning(f"LangChain question generation failed, using fallback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la génération de la question"
        )

@router.get("/question_result/{task_id}")
async def get_question_result(
    task_id: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère le résultat de la génération de questions (authentification requise)"""
    result = AsyncResult(task_id)
    if result.state == "PENDING":
        return {"status": "pending"}
    elif result.state == "SUCCESS":
        return {"status": "success", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "failure", "error": str(result.result)}
    else:
        return {"status": result.state}


# --- Nouveau: Analyse des résultats de quiz ---
@router.post("/analyze_quiz")
async def analyze_quiz(
    evaluation: dict = Body(..., description="Résultats détaillés du quiz"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Lance l'analyse d'un quiz complété (authentification requise).

    Détecte automatiquement si c'est le questionnaire initial de profilage :
    - Si aucun profil n'existe encore → initial = True
    - Si le profil existe mais questionnaire non complété → initial = True
    - Sinon → quiz normal
    """
    try:
        # Vérifier si le profil existe et/ou si le questionnaire initial a déjà été fait
        profile = await profile_service.get_profile_by_user_id(current_user.id)
        is_initial = False

        if not profile:
            # Aucun profil → c'est forcément le questionnaire initial
            is_initial = True
            logger.info(f"Detected initial questionnaire (no profile yet) for user {current_user.id}")
        elif not profile.questionnaire_initial_complete:
            # Profil existe mais questionnaire pas encore complété
            is_initial = True
            logger.info(f"Detected initial questionnaire (profile exists but not completed) for user {current_user.id}")

        u = UtilisateurRead.model_validate(current_user, from_attributes=True)
        user_dict = u.model_dump()

        # Extraire le domaine de l'utilisateur
        domaine = getattr(current_user, 'domaine', 'Général')
        if hasattr(current_user, 'etudiant') and current_user.etudiant:
            domaine = current_user.etudiant.domaine
        elif hasattr(current_user, 'professeur') and current_user.professeur:
            domaine = current_user.professeur.domaine

        # Lancer l'analyse avec le bon flag et le domaine
        task = profile_analysis_task.delay(user_dict, evaluation, is_initial, domaine)

        message = "Questionnaire initial en cours d'analyse" if is_initial else "Quiz en cours d'analyse"

        return {
            "task_id": task.id,
            "is_initial_questionnaire": is_initial,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error starting profile analysis: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse du quiz")


@router.get("/analysis_result/{task_id}")
async def get_analysis_result(
    task_id: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupère le résultat de l'analyse de quiz (authentification requise)"""
    result = AsyncResult(task_id)
    if result.state == "PENDING":
        return {"status": "pending"}
    elif result.state == "SUCCESS":
        return {"status": "success", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "failure", "error": str(result.result)}
    else:
        return {"status": result.state}


# ==================== NOUVEAUX ENDPOINTS GAMIFICATION ====================
# 🔒 Tous les endpoints de gamification nécessitent une authentification

@router.get("/gamification/badges")
async def get_available_badges(current_user: Utilisateur = Depends(get_current_user)):
    """Retourne la liste de tous les badges disponibles avec leurs descriptions (authentification requise)"""
    from src.profile.gamification import BADGE_CONFIG

    badges_list = []
    for badge_name, config in BADGE_CONFIG.items():
        badges_list.append({
            "name": badge_name,
            "category": config["category"],
            "description": config["description"],
            "xp_reward": config["xp_reward"],
            "condition": config["condition"]
        })

    return {
        "total_badges": len(badges_list),
        "badges": badges_list
    }


@router.get("/gamification/my-badges")
async def get_my_badges(current_user: Utilisateur = Depends(get_current_user)):
    """Retourne les badges de l'utilisateur avec leur progression"""
    from src.profile.gamification import BADGE_CONFIG

    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        raise ProfileNotFound()

    earned_badges = []
    locked_badges = []

    for badge_name, config in BADGE_CONFIG.items():
        badge_info = {
            "name": badge_name,
            "category": config["category"],
            "description": config["description"],
            "xp_reward": config["xp_reward"],
            "earned": badge_name in profile.badges
        }

        if badge_info["earned"]:
            earned_badges.append(badge_info)
        else:
            locked_badges.append(badge_info)

    return {
        "earned": earned_badges,
        "locked": locked_badges,
        "total_earned": len(earned_badges),
        "total_available": len(BADGE_CONFIG),
        "completion_percentage": round((len(earned_badges) / len(BADGE_CONFIG)) * 100, 1)
    }


@router.get("/gamification/streak")
async def get_streak_info(current_user: Utilisateur = Depends(get_current_user)):
    """Retourne les informations sur la série de jours consécutifs"""
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        raise ProfileNotFound()

    from src.profile.gamification import GamificationEngine

    streak_data = GamificationEngine.calculate_streak(
        profile.last_activity_date,
        profile.current_streak
    )

    return {
        "current_streak": streak_data["current_streak"],
        "best_streak": profile.best_streak,
        "is_active": streak_data["is_active"],
        "streak_broken": streak_data["streak_broken"],
        "days_since_last": streak_data["days_since_last"],
        "last_activity": profile.last_activity_date.isoformat() if profile.last_activity_date else None
    }


@router.get("/gamification/progression")
async def get_progression(current_user: Utilisateur = Depends(get_current_user)):
    """Retourne la progression détaillée de l'utilisateur (style boot.dev)"""
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        raise ProfileNotFound()

    from src.profile.gamification import GamificationEngine, format_profile_display

    # Calculer XP pour le niveau suivant
    current_level = profile.niveau
    xp_for_current = ((current_level - 1) ** 2) * 100 if current_level > 1 else 0
    xp_for_next = (current_level ** 2) * 100
    xp_progress = profile.xp - xp_for_current
    xp_needed = xp_for_next - xp_for_current
    progress_pct = (xp_progress / xp_needed * 100) if xp_needed > 0 else 0

    return {
        "level": {
            "current": current_level,
            "next": current_level + 1,
            "progress_percentage": round(progress_pct, 1)
        },
        "xp": {
            "total": profile.xp,
            "current_level": xp_progress,
            "needed_for_next": xp_needed,
            "total_earned": profile.total_xp_earned
        },
        "badges": {
            "total": len(profile.badges),
            "recent": profile.badges[-5:] if profile.badges else []
        },
        "streak": {
            "current": profile.current_streak,
            "best": profile.best_streak
        },
        "quiz": {
            "completed": profile.quiz_completed,
            "perfect_count": profile.perfect_quiz_count,
            "average_score": round(profile.statistiques.get("average_score", 0), 1) if profile.statistiques else 0
        }
    }


@router.get("/gamification/leaderboard-enriched")
async def get_enriched_leaderboard(
    current_user: Utilisateur = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Retourne le classement enrichi avec badges, streaks, etc. (authentification requise)

    SÉCURITÉ: Affiche username au lieu de UUID pour protéger la vie privée.
    Marque l'utilisateur connecté avec 'is_me': true
    """

    # Tenter de récupérer depuis le cache
    try:
        cached = await get_leaderboard_cache()
        if cached:
            # Marquer l'utilisateur connecté dans le cache
            for entry in cached[:limit]:
                entry["is_me"] = (entry.get("username") == current_user.username)
            return {"leaderboard": cached[:limit], "source": "cache"}
    except Exception as e:
        logger.warning(f"Redis unavailable for leaderboard: {e}")

    # Récupérer depuis la DB
    leaderboard_basic = await profile_service.get_leaderboard(limit)

    # Enrichir avec des données supplémentaires
    enriched = []
    for entry in leaderboard_basic:
        # Le leaderboard retourne maintenant username au lieu de UUID
        username = entry["username"]

        # Trouver le profil par username (on doit d'abord trouver l'UUID)
        # Pour l'instant, on va juste utiliser les données de base
        enriched.append({
            "rank": entry["rank"],
            "username": username,  # USERNAME SÉCURISÉ
            "niveau": entry["niveau"],
            "xp": entry["xp"],
            "badges_count": entry["badges_count"],
            "is_me": (username == current_user.username),  # Marquer si c'est l'utilisateur connecté
        })

    # Mettre en cache (sans le flag is_me)
    try:
        cache_data = [
            {k: v for k, v in item.items() if k != "is_me"}
            for item in enriched
        ]
        await set_leaderboard_cache(cache_data)
    except Exception as e:
        logger.warning(f"Failed to cache leaderboard: {e}")

    return {
        "leaderboard": enriched,
        "source": "database"
    }


@router.get("/gamification/dashboard")
async def get_gamification_dashboard(current_user: Utilisateur = Depends(get_current_user)):
    """Dashboard complet de gamification (pour l'interface utilisateur)"""
    profile = await profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        raise ProfileNotFound()

    from src.profile.gamification import GamificationEngine, format_profile_display

    # Formater le profil pour l'affichage
    display_data = format_profile_display(profile.model_dump())

    # Ajouter les recommandations
    display_data["recommendations"] = profile.recommandations or []

    # Ajouter les dernières analyses
    analyses = []
    if profile.analyse_detaillee:
        for key, value in list(profile.analyse_detaillee.items())[-5:]:
            if isinstance(value, dict):
                analyses.append(value)

    display_data["recent_analyses"] = analyses

    # Ajouter les dernières activités
    recent_activities = profile.historique_activites[-10:] if profile.historique_activites else []
    display_data["recent_activities"] = recent_activities

    return display_data


@router.get("/has-profile")
async def has_profile_endpoint(current_user: Utilisateur = Depends(get_current_user)):
    """Retourne un booléen indiquant si le profil MongoDB existe et le statut du questionnaire initial."""
    exists = await profile_service.has_profile(current_user.id)
    if not exists:
        return {"has_profile": False, "questionnaire_initial_complete": False}
    profil = await profile_service.get_profile_by_user_id(current_user.id)
    return {
        "has_profile": True,
        "questionnaire_initial_complete": bool(getattr(profil, 'questionnaire_initial_complete', False))
    }


# ==================== ROADMAP & COURS (GAMIFICATION) ====================

@router.get("/roadmap")
async def get_my_roadmap(current_user: Utilisateur = Depends(get_current_user)):
    """
    Récupère la roadmap active de l'utilisateur (cours personnalisé avec modules et leçons).

    Retourne:
    - Les modules avec leurs leçons et XP
    - La progression actuelle (% complétion, module actuel)
    - Les ressources à consulter pour progresser
    """
    from src.profile.roadmap_services import roadmap_service

    roadmap = await roadmap_service.get_active_roadmap(current_user.id)

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune roadmap trouvée. Complétez d'abord le questionnaire initial."
        )

    return {
        "roadmap": roadmap,
        "message": "Roadmap récupérée avec succès"
    }


@router.get("/courses/{course_id}")
async def get_course_details(
    course_id: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Récupère les détails complets d'un cours (modules, leçons, ressources, XP par leçon).

    Args:
        course_id: ID du cours

    Retourne:
    - Métadonnées du cours (titre, description, durée)
    - Liste des modules avec leçons
    - Progression de l'utilisateur
    - XP disponible par module/leçon
    """
    from src.profile.roadmap_services import roadmap_service

    # Récupérer le cours depuis MongoDB
    course = await roadmap_service.courses_collection.find_one({"course_id": course_id})

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cours introuvable"
        )

    # Vérifier que le cours appartient à l'utilisateur
    if course.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à ce cours"
        )

    # Récupérer la progression
    progression = await roadmap_service.get_user_progression(current_user.id, course_id)

    # Convertir ObjectId en string
    course["_id"] = str(course["_id"])

    return {
        "course": course,
        "progression": progression,
        "message": "Cours récupéré avec succès"
    }


@router.post("/courses/{course_id}/lessons/{lesson_id}/complete")
async def complete_lesson(
    course_id: str,
    lesson_id: str,
    time_spent_minutes: int = Body(default=10, ge=1, le=300),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Marque une leçon comme complétée et ajoute l'XP correspondant.

    Args:
        course_id: ID du cours
        lesson_id: ID de la leçon
        time_spent_minutes: Temps passé sur la leçon (pour stats)

    Retourne:
    - XP gagné
    - Nouvelle progression
    - Prochain objectif (leçon suivante ou module suivant)
    """
    from src.profile.roadmap_services import roadmap_service

    # Récupérer le cours pour connaître l'XP de la leçon
    course = await roadmap_service.courses_collection.find_one({"course_id": course_id})

    if not course or course.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )

    # Trouver l'XP de la leçon
    lesson_xp = 50  # XP par défaut
    for module in course.get("modules", []):
        for lesson in module.get("lessons", []):
            if lesson.get("id") == lesson_id:
                lesson_xp = lesson.get("xp", 50)
                break

    # Marquer la leçon comme complétée
    result = await roadmap_service.complete_lesson(
        user_id=current_user.id,
        course_id=course_id,
        lesson_id=lesson_id,
        xp_earned=lesson_xp
    )

    # Ajouter l'XP au profil global
    if result["status"] == "success":
        await profile_service.add_xp(current_user.id, lesson_xp)

        # Invalider les caches
        try:
            await invalidate_user_related_caches(current_user.id)
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

    return {
        "status": result["status"],
        "message": result["message"],
        "xp_earned": lesson_xp,
        "lesson_id": lesson_id
    }


@router.post("/courses/{course_id}/modules/{module_id}/complete")
async def complete_module(
    course_id: str,
    module_id: str,
    evaluation_score: float = Body(..., ge=0, le=100),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Marque un module comme complété après évaluation.

    Args:
        course_id: ID du cours
        module_id: ID du module
        evaluation_score: Score obtenu (0-100)

    Retourne:
    - Réussite/échec (seuil 70%)
    - XP gagné
    - Module suivant débloqué
    - Nouveau pourcentage de complétion du cours
    """
    from src.profile.roadmap_services import roadmap_service

    # Vérifier l'accès au cours
    course = await roadmap_service.courses_collection.find_one({"course_id": course_id})

    if not course or course.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )

    # XP pour complétion de module (200 XP si réussi)
    module_xp = 200 if evaluation_score >= 70 else 0

    result = await roadmap_service.complete_module(
        user_id=current_user.id,
        course_id=course_id,
        module_id=module_id,
        evaluation_score=evaluation_score,
        xp_earned=module_xp
    )

    # Ajouter l'XP au profil global si réussi
    if result.get("passed") and module_xp > 0:
        await profile_service.add_xp(current_user.id, module_xp)

        # Invalider les caches
        try:
            await invalidate_user_related_caches(current_user.id)
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

    return result


@router.get("/courses/{course_id}/progression")
async def get_course_progression(
    course_id: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Récupère la progression détaillée pour un cours spécifique.

    Retourne:
    - Pourcentage de complétion global
    - Modules complétés
    - Leçons complétées
    - XP gagné dans ce cours
    - Temps passé
    - Module/leçon actuelle
    """
    from src.profile.roadmap_services import roadmap_service

    progression = await roadmap_service.get_user_progression(current_user.id, course_id)

    if not progression:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune progression trouvée pour ce cours"
        )

    return {
        "progression": progression,
        "course_id": course_id
    }


@router.get("/courses/{course_id}/modules/{module_id}")
async def get_module_details(
    course_id: str,
    module_id: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Récupère les détails d'un module spécifique (leçons, ressources, XP).

    Utile pour afficher le contenu d'un module avant de le démarrer.
    """
    from src.profile.roadmap_services import roadmap_service

    course = await roadmap_service.courses_collection.find_one({"course_id": course_id})

    if not course or course.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )

    # Trouver le module
    target_module = None
    for module in course.get("modules", []):
        if module.get("id") == module_id:
            target_module = module
            break

    if not target_module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module introuvable"
        )

    # Récupérer la progression pour savoir si le module est complété
    progression = await roadmap_service.get_user_progression(current_user.id, course_id)

    is_completed = module_id in progression.get("completed_modules", []) if progression else False
    current_module = progression.get("current_module") == module_id if progression else False

    return {
        "module": target_module,
        "is_completed": is_completed,
        "is_current": current_module,
        "evaluation": progression.get("module_evaluations", {}).get(module_id) if progression else None
    }


@router.post("/courses/{course_id}/modules/{module_id}/start")
async def start_module(
    course_id: str,
    module_id: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Démarre un module (met à jour current_module dans la progression).
    """
    from src.profile.roadmap_services import roadmap_service

    result = await roadmap_service.update_module_progress(
        user_id=current_user.id,
        course_id=course_id,
        module_id=module_id,
        time_spent_minutes=0
    )

    return {
        "status": "success",
        "message": f"Module {module_id} démarré",
        "current_module": module_id
    }


@router.get("/statistics")
async def get_learning_statistics(current_user: Utilisateur = Depends(get_current_user)):
    """
    Statistiques globales d'apprentissage de l'utilisateur (tous cours confondus).

    Retourne:
    - Nombre de cours suivis/complétés
    - XP total gagné dans les cours
    - Temps total passé
    - Taux de complétion moyen
    """
    from src.profile.roadmap_services import roadmap_service

    stats = await roadmap_service.get_user_statistics(current_user.id)

    return {
        "statistics": stats,
        "user_id": str(current_user.id)
    }

