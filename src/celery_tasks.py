import asyncio
from celery import Celery
import logging
from asgiref.sync import async_to_sync

from src.mail import create_message, mail
from src.config import Config
from types import SimpleNamespace
import json
import re

# Configuration Celery
app = Celery(
    'tasks',
    broker=getattr(Config, 'REDIS_URL', None) or f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}",
    backend=getattr(Config, 'REDIS_URL', None) or f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}"
)

# Configuration supplémentaire
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_soft_time_limit=120,  # 120 secondes soft limit (augmenté pour LLM + roadmap)
    task_time_limit=180,  # 180 secondes hard limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Logger
logger = logging.getLogger(__name__)

# Loop utilitaire partagé par le worker Celery
_worker_loop = None

def _get_worker_loop():
    """Retourne une boucle event persistante pour éviter les fermetures intempestives."""
    global _worker_loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop
    except RuntimeError:
        pass
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_worker_loop)
    return _worker_loop


@app.task(bind=True, max_retries=3)
def send_email(self, recipients, subject, body):
    """
    Tâche d'envoi d'email asynchrone avec retry.
    Utilise une approche entièrement asynchrone pour éviter les blocages.
    """
    try:
        import asyncio

        message = create_message(recipients, subject, body)

        # Créer et exécuter une coroutine
        async def send_async():
            return await mail.send_message(message)

        # Essayer d'obtenir la boucle d'événement courante
        try:
            loop = asyncio.get_running_loop()
            # Si on est déjà dans une boucle, cela signifie qu'on est dans un contexte async
            # Ce ne devrait pas arriver dans une tâche Celery, mais on gère le cas
            logger.warning("Running loop detected, using asyncio.run may fail")
        except RuntimeError:
            # Pas de boucle d'événement actuelle, c'est normal
            loop = None

        # Exécuter avec asyncio.run qui crée une nouvelle boucle
        try:
            asyncio.run(send_async())
        except Exception as e:
            logger.error(f"asyncio.run failed: {e}, trying async_to_sync")
            from asgiref.sync import async_to_sync
            async_to_sync(send_async)()

        logger.info(f"✅ Email envoyé avec succès à: {recipients}")
        return {"status": "success", "message": f"Email envoyé à {recipients}"}

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'envoi d'email: {str(e)}")
        # Retry avec backoff exponentiel (2s, 4s, 8s)
        countdown = min(2 ** self.request.retries, 8)
        try:
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.critical(f"❌ Impossible d'envoyer l'email après {self.max_retries} tentatives: {recipients}")
            return {"status": "failed", "error": str(e), "max_retries_exceeded": True}


def _fallback_question(user: dict) -> str:
    """Fallback déterministe si LLM indisponible."""
    status = str(user.get('status', '') or '')
    if status == 'Etudiant':
        parts = []
        competences = user.get('competences') or []
        if competences:
            parts.append(f"Tu connais déjà {', '.join(competences)}.")
        objectifs = user.get('objectifs_apprentissage')
        if objectifs:
            parts.append(f"Ton objectif est: {objectifs}.")
        base = "Quelle est la prochaine compétence que tu aimerais développer dans les 2 semaines à venir ?"
        return (" ".join(parts) + " " + base).strip()
    if status == 'Professeur':
        parts = []
        specialites = user.get('specialites') or []
        if specialites:
            parts.append(f"Tes spécialités: {', '.join(specialites)}.")
        motiv = user.get('motivation_principale')
        if motiv:
            parts.append(f"Ta motivation principale: {motiv}.")
        base = "Quel est le principal défi pédagogique que tu souhaites adresser avec tes apprenants ?"
        return (" ".join(parts) + " " + base).strip()
    return "Quel est ton principal objectif d'apprentissage cette semaine ?"


def _clean_json_like(text: str):
    """Nettoie une sortie type Markdown ```json ... ``` et tente de parser en JSON."""
    if not isinstance(text, str):
        return None, None

    # 1. Enlever les fences ```json ... ``` ou ```...```
    cleaned = re.sub(r"^```(?:json)?\s*\n?|\n?```\s*$", "", text.strip())

    # 2. Enlever les espaces en début de lignes (indentation)
    lines = cleaned.split('\n')
    cleaned = '\n'.join(line.strip() for line in lines)

    # 3. Tenter de charger directement en JSON
    try:
        parsed = json.loads(cleaned)
        return cleaned, parsed
    except Exception:
        pass

    # 4. Tenter de trouver un objet JSON ou array dans le texte
    try:
        start_brace = cleaned.find('{')
        start_bracket = cleaned.find('[')

        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            depth = 0
            for i in range(start_brace, len(cleaned)):
                if cleaned[i] == '{':
                    depth += 1
                elif cleaned[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = cleaned[start_brace:i+1]
                        parsed = json.loads(json_str)
                        return json_str, parsed
        elif start_bracket != -1:
            depth = 0
            for i in range(start_bracket, len(cleaned)):
                if cleaned[i] == '[':
                    depth += 1
                elif cleaned[i] == ']':
                    depth -= 1
                    if depth == 0:
                        json_str = cleaned[start_bracket:i+1]
                        parsed = json.loads(json_str)
                        return json_str, parsed
    except Exception:
        pass

    return cleaned, None


@app.task(name="chatbot_task", bind=True)
def chatbot_task(self, user_id: str, session_id: str, message: str, user_context: dict = None):
    """Tâche async pour le chatbot IA - avec event loop propre"""
    import asyncio

    try:
        # Import à l'intérieur de la tâche pour éviter les effets de bord de fork
        from src.ai_agents.agents.chatbot_agent import ChatbotAgent
        from src.profile.learning_services import chatbot_service

        # Créer une instance locale (évite partage d'objets non fork-safe)
        local_agent = ChatbotAgent()

        # Créer un nouvel event loop pour ce worker (évite "Event loop is closed")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Exécuter le chatbot avec le nouvel event loop
        response = loop.run_until_complete(local_agent.chat(
            user_id=user_id,
            session_id=session_id,
            message=message,
            user_context=user_context
        ))

        # Sauvegarder dans MongoDB
        loop.run_until_complete(chatbot_service.add_message(
            utilisateur_id=user_id,
            session_id=session_id,
            role="user",
            content=message
        ))

        loop.run_until_complete(chatbot_service.add_message(
            utilisateur_id=user_id,
            session_id=session_id,
            role="assistant",
            content=response.get("response", "")
        ))

        return {
            "status": "success",
            "response": response,
            "task_id": self.request.id
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Erreur chatbot_task: {str(e)}")
        print(f"Traceback complet:\n{error_trace}")
        return {
            "status": "failed",
            "error": str(e),
            "traceback": error_trace,
            "task_id": self.request.id
        }


@app.task(name="module_completion_task", bind=True)
def module_completion_task(self, user_id: str, course_id: str, module_id: str, score: float, time_spent: int):
    """Tâche async pour la complétion de module"""
    try:
        from src.ai_agents.agents.course_manager_agent import course_manager_agent
        from src.profile.learning_services import progression_service
        from src.profile.services import profile_service

        # Valider la complétion
        validation_result = async_to_sync(course_manager_agent.validate_module_completion)(
            user_id=user_id,
            session_id=f"course_{course_id}",
            module_id=module_id,
            evaluation_results={
                "score": score,
                "seuil_reussite": 70
            }
        )

        if validation_result.get("module_completed"):
            # Marquer comme complété
            async_to_sync(progression_service.complete_module)(
                utilisateur_id=user_id,
                course_id=course_id,
                module_id=module_id,
                evaluation_result={
                    "score": score,
                    "passed": True,
                    "date": json.dumps(json.loads(json.dumps(str(__import__('datetime').datetime.now())))[:-1], default=str)
                }
            )

            # Ajouter du temps
            async_to_sync(progression_service.add_time_spent)(
                utilisateur_id=user_id,
                course_id=course_id,
                minutes=time_spent,
                module_id=module_id
            )

            # Gagner XP
            profil = async_to_sync(profile_service.get_profile_by_user_id)(user_id)
            if profil:
                async_to_sync(profile_service.add_xp)(
                    user_id,
                    validation_result.get("xp_gained", 200)
                )

        return {
            "status": "success",
            "validation_result": validation_result,
            "task_id": self.request.id
        }
    except Exception as e:
        print(f"Erreur module_completion_task: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }


@app.task(name="generate_profile_question_task")
def generate_profile_question_task(user_data: dict):
    """Génère une question personnalisée (LLM si dispo), sinon fallback.
    Retourne un objet avec question brute et JSON parsé si applicable.
    """
    try:
        try:
            from src.ai_agents.profiler.question_generator import generate_profile_question as llm_generate
        except Exception:
            llm_generate = None

        if llm_generate:
            try:
                # Utiliser un objet simple avec attributs pour satisfaire la signature attendue
                user_obj = SimpleNamespace(**user_data)
                question = llm_generate(user_obj)
                cleaned, parsed = _clean_json_like(question)
                if parsed and isinstance(parsed, list) and len(parsed) > 0:
                    return {"ok": True, "source": "llm", "question": cleaned or question, "json": parsed}
                else:
                    # Si le parsing échoue, utiliser le fallback
                    print(f"LLM parsing failed, using fallback. Raw: {question[:200] if question else 'None'}")
            except Exception as e:
                print(f"LLM generation failed: {e}, using fallback")
                # fallback si LLM échoue
                pass

        # Fallback: générer des questions de base
        q = _fallback_question(user_data)
        return {"ok": True, "source": "fallback", "question": q, "json": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.task(name="profile_analysis_task")
def profile_analysis_task(user_data: dict, evaluation: dict, is_initial: bool = False):
    """
    Analyse les résultats du quiz avec gamification complète et met à jour le profil.

    Args:
        user_data: Données de l'utilisateur
        evaluation: Résultats détaillés du quiz
        is_initial: Si True, c'est le questionnaire initial de profilage (fait UNE FOIS)

    Pour le questionnaire initial (is_initial=True):
    - Les questions ouvertes sont prioritaires pour évaluer le VRAI niveau
    - Les réponses sont sauvegardées dans MongoDB avec analyse sémantique
    - Utilise le LLM pour analyser les questions ouvertes en profondeur

    Pour les quiz normaux (is_initial=False):
    - Gamification complète avec XP, badges, streaks
    - Recommandations basées sur les performances
    """
    try:
        from src.ai_agents.profiler.profile_analyzer import analyze_profile_with_llm
        from src.profile.services import profile_service
        from uuid import UUID as _UUID

        print(f"[PROFILE_ANALYSIS] Starting analysis for user: {user_data.get('username', 'unknown')}")
        print(f"[PROFILE_ANALYSIS] Is initial questionnaire: {is_initial}")

        # 1) Extraire user_id
        user_id_raw = user_data.get('id')
        try:
            user_uuid = _UUID(str(user_id_raw))
        except Exception:
            user_uuid = str(user_id_raw)

        # 2) Analyser avec le LLM pour obtenir une évaluation approfondie
        llm_analysis = None
        try:
            user_json = json.dumps(user_data, default=str, ensure_ascii=False)
            evaluation_json = json.dumps(evaluation, ensure_ascii=False)

            print(f"[PROFILE_ANALYSIS] Calling LLM for deep analysis...")
            llm_text = analyze_profile_with_llm(user_json, evaluation_json)

            # Parser la réponse LLM
            cleaned, parsed = _clean_json_like(llm_text)

            if isinstance(parsed, dict):
                llm_analysis = parsed
                print(f"[PROFILE_ANALYSIS] LLM analysis completed successfully")
            else:
                print(f"[PROFILE_ANALYSIS] LLM parsing failed, continuing without LLM analysis")

        except Exception as llm_error:
            print(f"[PROFILE_ANALYSIS] LLM analysis failed: {llm_error}, continuing without it")

        # 3) Traiter selon le type de questionnaire
        if is_initial:
            # C'EST LE QUESTIONNAIRE INITIAL - Créer le profil puis sauvegarder les réponses
            print(f"[PROFILE_ANALYSIS] Processing initial questionnaire...")

            # ✅ ÉTAPE 1: Vérifier si le profil MongoDB existe, sinon le créer
            import asyncio

            async def _create_or_get_profile():
                profile = await profile_service.get_profile_by_user_id(user_uuid)

                if not profile:
                    print(f"[PROFILE_ANALYSIS] Creating MongoDB profile for user {user_uuid}")
                    from src.profile.schema import ProfilCreate

                    # Déterminer le niveau initial à partir du LLM ou fallback
                    initial_level = 1
                    initial_label = "débutant"
                    try:
                        if llm_analysis and isinstance(llm_analysis, dict):
                            lvl = int(llm_analysis.get("niveau", 0) or 0)
                            if 1 <= lvl <= 10:
                                initial_level = lvl
                                initial_label = llm_analysis.get("niveau_reel") or ("débutant" if lvl < 4 else "intermédiaire" if lvl < 7 else "avancé")
                        else:
                            # Fallback simple basé sur évaluation (score sur questions ouvertes si fourni)
                            quiz = evaluation or {}
                            score_open = quiz.get("score_questions_ouvertes") or 0
                            score_qcm = quiz.get("score_qcm") or 0
                            computed = round((score_open * 0.7 + score_qcm * 0.3))
                            if 1 <= computed <= 10:
                                initial_level = max(3, computed)  # ne pas afficher 1 si score élevé
                                initial_label = "débutant" if initial_level < 4 else "intermédiaire" if initial_level < 7 else "avancé"
                    except Exception:
                        pass

                    # Créer le profil MongoDB avec les données de base
                    profile_data = ProfilCreate(
                        utilisateur_id=user_uuid,
                        niveau=initial_level,
                        xp=0,
                        badges=[],
                        competences=[],
                        energie=5
                    )

                    try:
                        profile = await profile_service.create_profile(profile_data)
                        print(f"[PROFILE_ANALYSIS] MongoDB profile created: {profile.id}")
                    except Exception as e:
                        print(f"[PROFILE_ANALYSIS] Error creating profile: {e}")
                        profile = await profile_service.get_profile_by_user_id(user_uuid)
                        if not profile:
                            raise Exception(f"Failed to create profile for user {user_uuid}: {e}")
                else:
                    print(f"[PROFILE_ANALYSIS] MongoDB profile already exists: {profile.id}")

                return profile

            async def _save_questionnaire(profile):
                # ✅ ÉTAPE 2: Sauvegarder le questionnaire initial avec l'analyse LLM
                updated_profile = await profile_service.save_initial_questionnaire(
                    user_uuid,
                    evaluation,
                    analyse_llm=llm_analysis
                )
                # Mettre à jour le niveau et son libellé à partir de l’analyse LLM si disponible
                try:
                    update_fields = {}
                    if llm_analysis and isinstance(llm_analysis, dict):
                        lvl = llm_analysis.get("niveau")
                        if isinstance(lvl, (int, float)):
                            lvl = int(lvl)
                            if 1 <= lvl <= 10:
                                update_fields["niveau"] = lvl
                        label = llm_analysis.get("niveau_reel")
                        if isinstance(label, str) and label:
                            update_fields["niveau_reel"] = label
                    if update_fields:
                        await profile_service.collection.update_one(
                            {"utilisateur_id": str(user_uuid)},
                            {"$set": update_fields}
                        )
                        # Recharger
                        updated_profile = await profile_service.get_profile_by_user_id(user_uuid)
                except Exception as _e:
                    print(f"[PROFILE_ANALYSIS] Warning: could not update level from LLM analysis: {_e}")
                return updated_profile

            # Exécuter les opérations asynchrones dans une boucle d'événements isolée
            loop = None
            try:
                # Créer une NOUVELLE boucle pour éviter les conflits de session
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                profile = loop.run_until_complete(_create_or_get_profile())
                updated_profile = loop.run_until_complete(_save_questionnaire(profile))
            except Exception as e:
                print(f"[PROFILE_ANALYSIS] Async operation failed: {e}")
                raise
            finally:
                # Ne pas fermer la boucle ici, on en aura besoin plus bas
                pass

            # ✅ ÉTAPE 3: Créer le profil SQL Etudiant/Professeur après questionnaire (si absent)
            try:
                from src.users.services import UserService as _UserSvc
                from src.users.models import StatutUtilisateur as _StatutEnum
                status_val = user_data.get('status') or user_data.get('Statut') or 'Etudiant'
                try:
                    status_enum = _StatutEnum(status_val)
                except Exception:
                    status_enum = _StatutEnum.ETUDIANT
                # Détails possibles à mapper vers SQL (niveau, competences, etc.)
                details = {}
                if llm_analysis and isinstance(llm_analysis, dict):
                    details.update(llm_analysis)
                # fallback depuis evaluation
                if isinstance(evaluation, dict):
                    details.setdefault('competences', [])

                # Utiliser une NOUVELLE boucle pour SQLAlchemy async
                async def _ensure_sql_profile():
                    await _UserSvc.ensure_sql_profile_after_questionnaire(
                        user_uuid,
                        status_enum,
                        details
                    )

                # Utiliser une boucle isolée pour éviter les conflits SQLAlchemy
                sql_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(sql_loop)
                try:
                    sql_loop.run_until_complete(_ensure_sql_profile())
                finally:
                    sql_loop.close()

            except Exception as e:
                print(f"[PROFILE_ANALYSIS] Warning: could not ensure SQL profile: {e}")

            # Générer aussi des recommandations personnalisées
            recommendations = []
            if llm_analysis:
                recommendations = llm_analysis.get("recommandations", [])

            # Ajouter des recommandations génériques si pas assez du LLM
            if len(recommendations) < 3:
                recommendations.extend([
                    "📚 Commence par les fondamentaux de l'IA selon ton profil",
                    "🎯 Fixe-toi des objectifs d'apprentissage clairs",
                    "💪 Pratique régulièrement pour progresser"
                ])

            # Mettre à jour les recommandations dans le profil (réutiliser la même boucle)
            async def _update_recommendations():
                await profile_service.collection.update_one(
                    {"utilisateur_id": str(user_uuid)},
                    {"$set": {"recommandations": recommendations}}
                )

            try:
                if loop and not loop.is_closed():
                    loop.run_until_complete(_update_recommendations())
                else:
                    # Créer une nouvelle boucle si nécessaire
                    temp_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(temp_loop)
                    try:
                        temp_loop.run_until_complete(_update_recommendations())
                    finally:
                        temp_loop.close()
            except Exception as e:
                print(f"[PROFILE_ANALYSIS] Warning: failed to update recommendations: {e}")

            # Recharger le profil
            async def _reload_profile():
                return await profile_service.get_profile_by_user_id(user_uuid)

            try:
                if loop and not loop.is_closed():
                    updated_profile = loop.run_until_complete(_reload_profile())
                else:
                    # Créer une nouvelle boucle si nécessaire
                    temp_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(temp_loop)
                    try:
                        updated_profile = temp_loop.run_until_complete(_reload_profile())
                    finally:
                        temp_loop.close()
            except Exception as e:
                print(f"[PROFILE_ANALYSIS] Warning: failed to reload profile: {e}")
                # Utiliser le profil de l'étape 2
                pass

            prof_dict = updated_profile.model_dump() if hasattr(updated_profile, 'model_dump') else getattr(updated_profile, '__dict__', None)

            print(f"[PROFILE_ANALYSIS] Initial questionnaire saved successfully")

            # ✅ ÉTAPE 4: Générer la roadmap initiale en asynchrone (boucle isolée + timeout)
            print(f"[PROFILE_ANALYSIS] Generating initial roadmap based on profile...")
            roadmap = None
            try:
                from src.profile.roadmap_services import RoadmapService

                async def _generate_initial_roadmap():
                    roadmap_service = RoadmapService()
                    return await asyncio.wait_for(
                        roadmap_service.create_and_save_roadmap(
                            user_id=user_uuid,
                            profil=updated_profile,
                            duration_weeks=12,
                            force_regenerate=True
                        ),
                        timeout=60.0
                    )

                # Boucle isolée dédiée à la roadmap
                roadmap_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(roadmap_loop)
                try:
                    roadmap = roadmap_loop.run_until_complete(_generate_initial_roadmap())
                    print(f"[PROFILE_ANALYSIS] Initial roadmap generated successfully")
                finally:
                    roadmap_loop.close()
            except asyncio.TimeoutError:
                print(f"[PROFILE_ANALYSIS] Warning: Roadmap generation timed out (>60s), continuing without it")
            except Exception as e:
                print(f"[PROFILE_ANALYSIS] Warning: Failed to generate initial roadmap: {e}")


            # ✅ Nettoyer les caches/questionnaires pour ce user afin d'éviter de réafficher d'anciens résultats
            try:
                from src.db.redis import r_sync as redis_client

                # Utiliser uniquement des appels synchrones Redis
                pattern = f"questionnaire:{user_uuid}:*"
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
                # Nettoyer un cache éventuel de profil/questionnaire
                redis_client.delete(f"profile:{user_uuid}")
                redis_client.delete(f"questionnaire_result:{user_uuid}")
                print(f"[PROFILE_ANALYSIS] Cache cleared for user {user_uuid}")
            except Exception as cache_err:
                print(f"[PROFILE_ANALYSIS] Warning: cache clear failed: {cache_err}")

            # ✅ ÉTAPE 5: S'assurer que le flag questionnaire_initial_complete est bien à True
            async def _ensure_questionnaire_flag():
                try:
                    # Forcer une dernière mise à jour pour garantir que le flag est bien enregistré
                    await profile_service.collection.update_one(
                        {"utilisateur_id": str(user_uuid)},
                        {"$set": {"questionnaire_initial_complete": True}}
                    )
                    print(f"[PROFILE_ANALYSIS] Ensured questionnaire_initial_complete flag is True for user {user_uuid}")
                except Exception as flag_err:
                    print(f"[PROFILE_ANALYSIS] Warning: could not ensure questionnaire_initial_complete flag: {flag_err}")

            try:
                if loop and not loop.is_closed():
                    loop.run_until_complete(_ensure_questionnaire_flag())
                else:
                    temp_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(temp_loop)
                    try:
                        temp_loop.run_until_complete(_ensure_questionnaire_flag())
                    finally:
                        temp_loop.close()
            except Exception as e:
                print(f"[PROFILE_ANALYSIS] Warning: failed to ensure questionnaire flag: {e}")

            return {
                "ok": True,
                "is_initial": True,
                "profile": prof_dict,
                "questionnaire_complete": True,
                "analyse_questions_ouvertes": updated_profile.analyse_questions_ouvertes,
                "recommendations": recommendations,
                "llm_analysis": llm_analysis,
                "roadmap_generated": roadmap is not None,
                "roadmap": roadmap if roadmap else None,
            }

        else:
            # QUIZ NORMAL - Gamification complète
            print(f"[PROFILE_ANALYSIS] Processing normal quiz with gamification...")
            import asyncio

            time_taken = evaluation.get("time_taken_seconds")

            async def _analyze_quiz():
                return await profile_service.analyze_quiz_and_update_profile(
                    user_uuid,
                    evaluation,
                    time_taken_seconds=time_taken
                )

            # Créer une NOUVELLE boucle pour éviter les conflits
            quiz_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(quiz_loop)
            try:
                result = quiz_loop.run_until_complete(_analyze_quiz())
            finally:
                pass  # Ne pas fermer immédiatement

            print(f"[PROFILE_ANALYSIS] Gamification complete. XP earned: {result['xp_earned']['total_xp']}")
            print(f"[PROFILE_ANALYSIS] Badges earned: {result['badges_earned']}")
            print(f"[PROFILE_ANALYSIS] Level: {result['old_level']} -> {result['new_level']}")

            # Enrichir les recommandations avec celles du LLM
            if llm_analysis:
                llm_recommendations = llm_analysis.get("recommandations", [])
                if llm_recommendations:
                    result["recommendations"].extend(llm_recommendations)
                    # Dédupliquer
                    result["recommendations"] = list(dict.fromkeys(result["recommendations"]))

                result["llm_analysis"] = llm_analysis

                # Mettre à jour les recommandations dans MongoDB
                async def _update_recommendations():
                    await profile_service.collection.update_one(
                        {"utilisateur_id": str(user_uuid)},
                        {"$set": {"recommandations": result["recommendations"]}}
                    )

                try:
                    quiz_loop.run_until_complete(_update_recommendations())
                except Exception as e:
                    print(f"[PROFILE_ANALYSIS] Warning: failed to update quiz recommendations: {e}")
                finally:
                    quiz_loop.close()
            else:
                quiz_loop.close()


            # Formatter le profil pour la réponse
            prof_dict = result["profile"].model_dump() if hasattr(result["profile"], 'model_dump') else getattr(result["profile"], '__dict__', None)

            print(f"[PROFILE_ANALYSIS] Quiz analysis completed successfully")

            return {
                "ok": True,
                "is_initial": False,
                "profile": prof_dict,
                "xp_earned": result["xp_earned"],
                "badges_earned": result["badges_earned"],
                "level_up": result["level_up"],
                "old_level": result["old_level"],
                "new_level": result["new_level"],
                "streak_info": result["streak_info"],
                "quiz_summary": result["quiz_summary"],
                "performance_analysis": result["performance_analysis"],
                "recommendations": result["recommendations"][:10],  # Limiter à 10 recommandations
            }

    except Exception as e:
        print(f"[PROFILE_ANALYSIS] Task failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


# ==================== CHATBOT STREAMING (SCALABLE) ====================

@app.task(name="chatbot_streaming_task", bind=True)
def chatbot_streaming_task(self, user_id: str, session_id: str, message: str):
    """
    Tâche Celery qui stream la réponse GPT-4 via Redis Pub/Sub.

    Cette approche permet:
    - Réponse FastAPI immédiate (non bloquée)
    - Streaming temps réel via WebSocket
    - Scalabilité à 10,000+ utilisateurs simultanés

    Args:
        user_id: ID de l'utilisateur
        session_id: ID de session
        message: Message de l'utilisateur

    Returns:
        Dict avec la réponse complète et les métadonnées
    """
    from openai import OpenAI
    from src.db.redis import r_sync as redis_client
    from src.profile.services import profile_service
    from src.profile.learning_services import chatbot_service
    from src.ai_agents.agents.chatbot_agent import CHATBOT_SYSTEM_PROMPT
    from datetime import datetime, UTC

    task_id = self.request.id
    channel = f"chatbot_stream:{task_id}"

    try:
        print(f"[CHATBOT_STREAMING] Task {task_id} started for user {user_id}")

        # 1. Récupérer le profil utilisateur
        profil = async_to_sync(profile_service.get_profile_by_user_id)(user_id)

        user_context = {}
        if profil:
            user_context = {
                "niveau_technique": profil.niveau,
                "competences": profil.competences,
                "objectifs": profil.objectifs,
                "xp": profil.xp,
                "badges": profil.badges
            }

        # 2. Construire le contexte pour le prompt
        context_str = f"""
PROFIL APPRENANT :
- Niveau : {user_context.get('niveau_technique', 5)}/10
- Compétences : {', '.join(user_context.get('competences', [])) or 'Non identifiées'}
- Objectifs : {user_context.get('objectifs', 'Non définis')}
- XP : {user_context.get('xp', 0)}
"""

        # 3. Construire les messages pour OpenAI
        messages = [
            {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
            {"role": "system", "content": f"CONTEXTE UTILISATEUR:\n{context_str}"},
            {"role": "user", "content": message}
        ]

        # 4. Stream depuis OpenAI
        client = OpenAI(api_key=Config.OPENAI_API_KEY)

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            temperature=0.7
        )

        full_response = ""
        chunk_count = 0

        # Publier le début du streaming
        redis_client.publish(
            channel,
            json.dumps({
                "type": "stream_started",
                "task_id": task_id,
                "timestamp": datetime.now(UTC).isoformat()
            })
        )

        # 5. Stream les chunks
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                chunk_count += 1

                # Publier le chunk sur Redis
                redis_client.publish(
                    channel,
                    json.dumps({
                        "type": "chunk",
                        "content": content,
                        "chunk_number": chunk_count,
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                )

        print(f"[CHATBOT_STREAMING] Streamed {chunk_count} chunks, total length: {len(full_response)}")

        # 6. Analyser l'intention
        message_lower = message.lower()
        intentions = {
            "concept_question": any(word in message_lower for word in ["qu'est-ce", "comment", "pourquoi", "expliquer", "définir"]),
            "code_help": any(word in message_lower for word in ["code", "erreur", "bug", "implémenter"]),
            "resource_request": any(word in message_lower for word in ["ressource", "cours", "tutoriel", "livre", "vidéo"]),
            "motivation": any(word in message_lower for word in ["difficile", "bloqué", "abandonner", "démotivé"]),
        }

        primary_intention = max(intentions.items(), key=lambda x: x[1])

        intention = {
            "primary": primary_intention[0],
            "confidence": 0.8 if primary_intention[1] else 0.3,
            "all_intentions": {k: v for k, v in intentions.items() if v}
        }

        # 7. Générer des suggestions
        suggestions_map = {
            "concept_question": [
                "💡 Peux-tu me donner un exemple concret ?",
                "📊 Montre-moi un cas d'utilisation",
                "🔗 Quel est le lien avec ce que j'ai déjà appris ?"
            ],
            "code_help": [
                "🔍 Où se trouve exactement l'erreur ?",
                "💻 Montre-moi comment déboguer",
                "📝 Quelles sont les bonnes pratiques ?"
            ],
            "resource_request": [
                "📚 Quelles ressources pour mon niveau ?",
                "🎥 Y a-t-il des vidéos recommandées ?",
                "💼 Des projets pratiques à faire ?"
            ],
            "motivation": [
                "🎯 Quels sont mes progrès jusqu'ici ?",
                "⚡ Comment rester motivé ?",
                "🏆 Quels sont mes prochains objectifs ?"
            ]
        }

        suggestions = suggestions_map.get(intention["primary"], [
            "💬 Pose-moi une question",
            "📚 Voir mes cours",
            "📊 Voir ma progression"
        ])

        # 8. Publier le message de complétion
        redis_client.publish(
            channel,
            json.dumps({
                "type": "complete",
                "full_response": full_response,
                "intention": intention,
                "suggestions": suggestions,
                "timestamp": datetime.now(UTC).isoformat(),
                "stats": {
                    "chunks": chunk_count,
                    "length": len(full_response),
                    "session_id": session_id
                }
            })
        )

        # 9. Sauvegarder dans MongoDB
        try:
            async_to_sync(chatbot_service.add_message)(
                utilisateur_id=user_id,
                session_id=session_id,
                role="user",
                content=message
            )

            async_to_sync(chatbot_service.add_message)(
                utilisateur_id=user_id,
                session_id=session_id,
                role="assistant",
                content=full_response,
                intention=intention
            )
        except Exception as db_error:
            print(f"[CHATBOT_STREAMING] Warning: Failed to save to MongoDB: {db_error}")

        print(f"[CHATBOT_STREAMING] Task {task_id} completed successfully")

        return {
            "status": "success",
            "response": full_response,
            "intention": intention,
            "suggestions": suggestions,
            "chunks_sent": chunk_count,
            "task_id": task_id
        }

    except Exception as e:
        error_msg = str(e)
        print(f"[CHATBOT_STREAMING] Task {task_id} failed: {error_msg}")
        import traceback
        traceback.print_exc()

        # Publier l'erreur sur Redis
        try:
            redis_client.publish(
                channel,
                json.dumps({
                    "type": "error",
                    "error": error_msg,
                    "timestamp": datetime.now(UTC).isoformat()
                })
            )
        except:
            pass

        return {
            "status": "error",
            "error": error_msg,
            "task_id": task_id
        }


# ==================== COURSE GENERATION (ASYNC) ====================

@app.task(name="generate_course_roadmap_task")
def generate_course_roadmap_task(user_id: str, course_topic: str, user_level: int, user_objectives: str, duration_weeks: int):
    """
    Tâche Celery pour générer une roadmap de cours personnalisée.

    Cette approche permet:
    - Réponse FastAPI immédiate (non bloquée)
    - Génération asynchrone de la roadmap en arrière-plan
    - Économie de ressources serveur

    Args:
        user_id: ID de l'utilisateur
        course_topic: Sujet du cours
        user_level: Niveau de l'utilisateur
        user_objectives: Objectifs d'apprentissage
        duration_weeks: Durée en semaines

    Returns:
        Dict avec la roadmap générée et cours créé
    """
    try:
        import asyncio
        from src.ai_agents.agents.course_manager_agent import course_manager_agent
        from src.profile.learning_services import course_service
        from src.profile.learning_services import progression_service
        from uuid import UUID as _UUID

        user_uuid = _UUID(str(user_id))

        print(f"[COURSE_GENERATION] Starting roadmap generation for user {user_id}")
        print(f"[COURSE_GENERATION] Topic: {course_topic}, Level: {user_level}, Weeks: {duration_weeks}")

        # Créer une nouvelle boucle d'événements pour cette opération async
        async def _generate_roadmap():
            # Générer la roadmap avec l'agent IA
            print(f"[COURSE_GENERATION] Calling course_manager_agent...")
            roadmap = await course_manager_agent.create_course_roadmap(
                course_topic=course_topic,
                user_level=user_level,
                user_objectives=user_objectives,
                duration_weeks=duration_weeks
            )
            print(f"[COURSE_GENERATION] Roadmap generated: {roadmap.get('titre')}")

            # Sauvegarder le cours dans MongoDB
            print(f"[COURSE_GENERATION] Saving course to MongoDB...")
            course_id = await course_service.create_course(roadmap)
            print(f"[COURSE_GENERATION] Course created with ID: {course_id}")

            # Créer la progression pour l'utilisateur
            print(f"[COURSE_GENERATION] Creating progression...")
            await progression_service.create_progression(
                utilisateur_id=user_uuid,
                course_id=roadmap["cours"]["id"]
            )

            # Incrémenter les inscriptions
            print(f"[COURSE_GENERATION] Incrementing enrollment...")
            await course_service.increment_enrollment(roadmap["cours"]["id"])

            return {
                "course_id": course_id,
                "roadmap": roadmap
            }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_generate_roadmap())
        finally:
            loop.close()

        print(f"[COURSE_GENERATION] Roadmap generation completed successfully")

        return {
            "ok": True,
            "course_id": result["course_id"],
            "roadmap": result["roadmap"]
        }

    except Exception as e:
        print(f"[COURSE_GENERATION] Task failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e)
        }

