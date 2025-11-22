from celery import Celery
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
)

@app.task
def send_email(recipients, subject, body):
    """Tâche d'envoi d'email asynchrone"""
    try:
        message = create_message(recipients, subject, body)
        async_to_sync(mail.send_message)(message)
        print(f"sent email to: {recipients}")
        return {"status": "success", "message": f"Email envoyé à {recipients}"}
    except Exception as e:
        print(e)
        return {"status": "failed", "error": str(e)}


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
    except Exception as e1:
        pass

    # 4. Tenter de trouver un objet JSON ou array dans le texte
    # Chercher entre { } ou [ ]
    try:
        # Trouver le premier { ou [
        start_brace = cleaned.find('{')
        start_bracket = cleaned.find('[')

        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            # Commencer par {
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
            # Commencer par [
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
    except Exception as e2:
        pass

    # 5. Tenter avec unescaping des caractères Unicode
    try:
        unescaped = cleaned.encode('utf-8').decode('unicode_escape')
        parsed = json.loads(unescaped)
        return unescaped, parsed
    except Exception:
        pass

    # 6. Remplacer les guillemets simples par doubles (cas courant)
    try:
        # Attention: ceci est un hack et peut causer des problèmes
        fixed = cleaned.replace("'", '"')
        parsed = json.loads(fixed)
        return fixed, parsed
    except Exception:
        pass

    # 7. Nettoyer les caractères de contrôle
    try:
        # Enlever les caractères de contrôle sauf \n, \r, \t
        import string
        printable = set(string.printable)
        cleaned_chars = ''.join(c for c in cleaned if c in printable)
        parsed = json.loads(cleaned_chars)
        return cleaned_chars, parsed
    except Exception:
        pass

    return cleaned, None


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
            profile = async_to_sync(profile_service.get_profile_by_user_id)(user_uuid)

            if not profile:
                print(f"[PROFILE_ANALYSIS] Creating MongoDB profile for user {user_uuid}")
                from src.profile.schema import ProfilCreate

                # Créer le profil MongoDB avec les données de base
                profile_data = ProfilCreate(
                    utilisateur_id=user_uuid,
                    niveau=1,  # Niveau par défaut, sera mis à jour par l'analyse
                    xp=0,
                    badges=[],
                    competences=[],
                    energie=5
                )

                try:
                    profile = async_to_sync(profile_service.create_profile)(profile_data)
                    print(f"[PROFILE_ANALYSIS] MongoDB profile created: {profile.id}")
                except Exception as e:
                    print(f"[PROFILE_ANALYSIS] Error creating profile: {e}")
                    # Réessayer de récupérer au cas où il a été créé entre-temps
                    profile = async_to_sync(profile_service.get_profile_by_user_id)(user_uuid)
                    if not profile:
                        raise Exception(f"Failed to create profile for user {user_uuid}: {e}")
            else:
                print(f"[PROFILE_ANALYSIS] MongoDB profile already exists: {profile.id}")

            # ✅ ÉTAPE 2: Sauvegarder le questionnaire initial avec l'analyse LLM
            updated_profile = async_to_sync(profile_service.save_initial_questionnaire)(
                user_uuid,
                evaluation,
                analyse_llm=llm_analysis
            )

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
                async_to_sync(_UserSvc.ensure_sql_profile_after_questionnaire)(
                    user_uuid,
                    status_enum,
                    details
                )
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

            # Mettre à jour les recommandations dans le profil
            async_to_sync(profile_service.collection.update_one)(
                {"utilisateur_id": str(user_uuid)},
                {"$set": {"recommandations": recommendations}}
            )

            # Recharger le profil
            updated_profile = async_to_sync(profile_service.get_profile_by_user_id)(user_uuid)

            prof_dict = updated_profile.model_dump() if hasattr(updated_profile, 'model_dump') else getattr(updated_profile, '__dict__', None)

            print(f"[PROFILE_ANALYSIS] Initial questionnaire saved successfully")

            return {
                "ok": True,
                "is_initial": True,
                "profile": prof_dict,
                "questionnaire_complete": True,
                "analyse_questions_ouvertes": updated_profile.analyse_questions_ouvertes,
                "recommendations": recommendations,
                "llm_analysis": llm_analysis,
            }

        else:
            # QUIZ NORMAL - Gamification complète
            print(f"[PROFILE_ANALYSIS] Processing normal quiz with gamification...")

            time_taken = evaluation.get("time_taken_seconds")

            result = async_to_sync(profile_service.analyze_quiz_and_update_profile)(
                user_uuid,
                evaluation,
                time_taken_seconds=time_taken
            )

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
                async_to_sync(profile_service.collection.update_one)(
                    {"utilisateur_id": str(user_uuid)},
                    {"$set": {"recommandations": result["recommendations"]}}
                )

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
