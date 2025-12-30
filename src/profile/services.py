from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.db.mongo_db import async_mongo_db
from src.profile.mongo_models import ProfilMongoDB
from src.profile.schema import ProfilCreate, ProfilUpdate
from src.profile.gamification import (
    GamificationEngine,
    BADGE_CONFIG
)


class ProfileService:
    """Service pour gérer les profils utilisateurs dans MongoDB"""

    def __init__(self):
        self.collection = async_mongo_db.profils

    async def create_profile(self, profile_data: ProfilCreate) -> ProfilMongoDB:
        """Créer un nouveau profil utilisateur"""

        # Vérifier si le profil existe déjà
        existing = await self.get_profile_by_user_id(profile_data.utilisateur_id)
        if existing:
            raise ValueError(f"Profile already exists for user {profile_data.utilisateur_id}")

        profil_dict = profile_data.model_dump()
        profil_dict["created_at"] = datetime.now()
        profil_dict["updated_at"] = datetime.now()
        profil_dict["utilisateur_id"] = str(profil_dict["utilisateur_id"])

        try:
            result = await self.collection.insert_one(profil_dict)
            created_profil = await self.collection.find_one({"_id": result.inserted_id})
            return ProfilMongoDB(**created_profil)
        except DuplicateKeyError:
            raise ValueError(f"Profile already exists for user {profile_data.utilisateur_id}")

    async def get_profile_by_user_id(self, user_id: UUID) -> Optional[ProfilMongoDB]:
        """Récupérer le profil d'un utilisateur par son ID"""
        profil_data = await self.collection.find_one({"utilisateur_id": str(user_id)})
        if profil_data:
            return ProfilMongoDB(**profil_data)
        return None

    async def get_profile_by_id(self, profile_id: str) -> Optional[ProfilMongoDB]:
        """Récupérer un profil par son ID MongoDB"""
        if not ObjectId.is_valid(profile_id):
            return None

        profil_data = await self.collection.find_one({"_id": ObjectId(profile_id)})
        if profil_data:
            return ProfilMongoDB(**profil_data)
        return None

    async def update_profile(self, user_id: UUID, update_data: ProfilUpdate) -> Optional[ProfilMongoDB]:
        """Mettre à jour le profil d'un utilisateur"""
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = datetime.now()

        result = await self.collection.find_one_and_update(
            {"utilisateur_id": str(user_id)},
            {"$set": update_dict},
            return_document=True
        )

        if result:
            return ProfilMongoDB(**result)
        return None

    async def delete_profile(self, user_id: UUID) -> bool:
        """Supprimer le profil d'un utilisateur"""
        result = await self.collection.delete_one({"utilisateur_id": str(user_id)})
        return result.deleted_count > 0

    async def add_xp(self, user_id: UUID, xp_points: int) -> Optional[ProfilMongoDB]:
        """Ajouter des points d'expérience et gérer les montées de niveau"""
        result = await self.collection.find_one_and_update(
            {"utilisateur_id": str(user_id)},
            {
                "$inc": {"xp": xp_points},
                "$set": {"updated_at": datetime.now()}
            },
            return_document=True
        )

        if result:
            profil = ProfilMongoDB(**result)
            await self._check_level_up(profil)
            # Récupérer le profil mis à jour
            updated_profil = await self.collection.find_one({"_id": profil.id})
            return ProfilMongoDB(**updated_profil) if updated_profil else profil
        return None

    async def add_badge(self, user_id: UUID, badge: str) -> Optional[ProfilMongoDB]:
        """Ajouter un badge au profil"""
        result = await self.collection.find_one_and_update(
            {"utilisateur_id": str(user_id)},
            {
                "$addToSet": {"badges": badge},
                "$set": {"updated_at": datetime.now()}
            },
            return_document=True
        )

        if result:
            return ProfilMongoDB(**result)
        return None

    async def add_competence(self, user_id: UUID, competence: str) -> Optional[ProfilMongoDB]:
        """Ajouter une compétence au profil"""
        result = await self.collection.find_one_and_update(
            {"utilisateur_id": str(user_id)},
            {
                "$addToSet": {"competences": competence},
                "$set": {"updated_at": datetime.now()}
            },
            return_document=True
        )

        if result:
            return ProfilMongoDB(**result)
        return None

    async def log_activity(self, user_id: UUID, activity_type: str, details: Dict[str, Any]) -> Optional[ProfilMongoDB]:
        """Enregistrer une activité dans l'historique"""
        activity = {
            "type": activity_type,
            "details": details,
            "timestamp": datetime.now()
        }

        result = await self.collection.find_one_and_update(
            {"utilisateur_id": str(user_id)},
            {
                "$push": {"historique_activites": activity},
                "$set": {"updated_at": datetime.now()}
            },
            return_document=True
        )

        if result:
            return ProfilMongoDB(**result)
        return None

    async def update_preferences(self, user_id: UUID, preferences: Dict[str, Any]) -> Optional[ProfilMongoDB]:
        """Mettre à jour les préférences utilisateur"""
        result = await self.collection.find_one_and_update(
            {"utilisateur_id": str(user_id)},
            {
                "$set": {
                    "preferences": preferences,
                    "updated_at": datetime.now()
                }
            },
            return_document=True
        )

        if result:
            return ProfilMongoDB(**result)
        return None

    async def get_profile_stats(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Obtenir les statistiques du profil"""
        profil = await self.get_profile_by_user_id(user_id)
        if not profil:
            return None

        return {
            "niveau": profil.niveau,
            "xp": profil.xp,
            "xp_pour_niveau_suivant": (profil.niveau * 1000) - profil.xp,
            "nombre_badges": len(profil.badges),
            "nombre_competences": len(profil.competences),
            "nombre_activites": len(profil.historique_activites),
            "energie": profil.energie
        }

    async def complete_activity(self, user_id: UUID, activity_type: str, xp_reward: int = 0) -> Optional[ProfilMongoDB]:
        """Enregistrer une activité et donner de l'XP"""
        activity_details = {
            "xp_earned": xp_reward,
            "completed_at": datetime.now()
        }

        profile = await self.log_activity(user_id, activity_type, activity_details)

        if xp_reward > 0 and profile:
            profile = await self.add_xp(user_id, xp_reward)

        return profile

    async def unlock_achievement(self, user_id: UUID, achievement: str, badge: str = None) -> Optional[ProfilMongoDB]:
        """Débloquer un succès et optionnellement un badge"""
        await self.log_activity(user_id, "achievement_unlocked", {"achievement": achievement})

        if badge:
            return await self.add_badge(user_id, badge)

        return await self.get_profile_by_user_id(user_id)

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtenir le classement des utilisateurs par XP (anonymisé)
        Retourne username au lieu de UUID pour protéger la vie privée
        """
        from src.db.main import get_session
        from src.users.models import Utilisateur
        from sqlmodel import select

        cursor = self.collection.find({}).sort("xp", -1).limit(limit)
        profiles = await cursor.to_list(length=limit)

        leaderboard = []

        # Récupérer les usernames depuis PostgreSQL
        async with get_session() as session:
            for i, profil_data in enumerate(profiles, 1):
                profil = ProfilMongoDB(**profil_data)

                # Récupérer le username de l'utilisateur
                stmt = select(Utilisateur.username).where(Utilisateur.id == profil.utilisateur_id)
                result = await session.execute(stmt)
                user = result.first()

                username = user[0] if user else "Utilisateur anonyme"

                leaderboard.append({
                    "rank": i,
                    "username": username,  # USERNAME au lieu de UUID
                    "niveau": profil.niveau,
                    "xp": profil.xp,
                    "badges_count": len(profil.badges)
                })

        return leaderboard

    async def _check_level_up(self, profil: ProfilMongoDB) -> None:
        """Vérifier et mettre à jour le niveau basé sur l'XP"""
        nouveau_niveau = profil.xp // 1000 + 1

        if nouveau_niveau > profil.niveau:
            await self.collection.update_one(
                {"_id": profil.id},
                {
                    "$set": {
                        "niveau": nouveau_niveau,
                        "updated_at": datetime.now()
                    }
                }
            )

    async def analyze_quiz_and_update_profile(
        self,
        user_id: UUID,
        evaluation: dict,
        time_taken_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyse complète d'un quiz avec gamification (style boot.dev)

        Args:
            user_id: UUID de l'utilisateur
            evaluation: Résultats du quiz avec questions et réponses
            time_taken_seconds: Temps pris pour compléter le quiz (optionnel)

        Returns:
            {
                "profile": ProfilMongoDB mis à jour,
                "xp_earned": {...},
                "badges_earned": [...],
                "level_up": bool,
                "streak_info": {...},
                "analysis": {...},
                "recommendations": [...]
            }
        """
        profile = await self.get_profile_by_user_id(user_id)
        if not profile:
            raise ValueError("Profile not found")

        # 1. Extraire les données du quiz
        questions_data = evaluation.get("questions_data", [])
        if not questions_data:
            # Fallback pour ancien format
            questions_data = evaluation.get("questions", [])
            if not questions_data:
                questions_data = evaluation.get("json", [])

        if not isinstance(questions_data, list):
            raise ValueError("Invalid evaluation format: expected list of questions")

        total_questions = len(questions_data)
        correct_answers = 0

        # Analyser chaque question pour déterminer si correcte
        for q in questions_data:
            is_correct = False

            # Différentes façons de déterminer si correct
            if isinstance(q.get("is_correct"), bool):
                is_correct = q["is_correct"]
            elif "correct" in q and isinstance(q["correct"], bool):
                is_correct = q["correct"]
            else:
                # Comparer la réponse avec la correction
                user_answer = str(q.get("user_answer", "")).strip().upper()
                correct_answer = str(q.get("correction", "")).strip()

                if correct_answer and user_answer:
                    # Extraire la lettre de la réponse correcte (ex: "A - Explication" -> "A")
                    correct_letter = correct_answer.split("-")[0].strip().upper()
                    answer_letter = user_answer.split(".")[0].strip().upper()

                    is_correct = answer_letter == correct_letter

            # Mettre à jour le champ is_correct
            q["is_correct"] = is_correct

            if is_correct:
                correct_answers += 1

        score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0

        # 2. Calculer la streak
        now = datetime.now()
        quiz_hour = now.hour

        streak_info = GamificationEngine.calculate_streak(
            profile.last_activity_date,
            profile.current_streak
        )

        new_streak = streak_info["current_streak"]
        is_new_streak_record = new_streak > profile.best_streak

        # 3. Calculer l'XP avec tous les bonus
        xp_calc = GamificationEngine.calculate_quiz_xp(
            score_percentage=score_percentage,
            total_questions=total_questions,
            correct_answers=correct_answers,
            time_taken_seconds=time_taken_seconds,
            current_streak=new_streak,
            quiz_hour=quiz_hour
        )

        xp_earned = xp_calc["total_xp"]
        old_level = profile.niveau
        new_xp_total = profile.xp + xp_earned
        new_level = GamificationEngine.calculate_level(new_xp_total)
        level_up = new_level > old_level

        # 4. Analyser la performance
        performance = GamificationEngine.analyze_quiz_performance(questions_data)

        # 5. Vérifier les nouveaux badges
        is_perfect = score_percentage >= 100

        # Mettre à jour les statistiques temporaires pour la vérification des badges
        temp_stats = {
            "niveau": new_level,
            "badges": profile.badges,
            "statistiques": {
                "current_streak": new_streak,
                "quiz_completed": profile.quiz_completed + 1,
                "perfect_quiz_count": profile.perfect_quiz_count + (1 if is_perfect else 0),
            }
        }

        quiz_result = {
            "score_percentage": score_percentage,
            "completed_at": now,
            "time_taken": time_taken_seconds
        }

        new_badges = GamificationEngine.check_new_badges(temp_stats, quiz_result)

        # Calculer XP bonus des badges
        badge_xp = sum(BADGE_CONFIG.get(badge, {}).get("xp_reward", 0) for badge in new_badges)
        if badge_xp > 0:
            xp_earned += badge_xp
            new_xp_total += badge_xp
            new_level = GamificationEngine.calculate_level(new_xp_total)

        # 6. Générer des recommandations personnalisées basées sur la performance
        recommendations = performance["recommendations"]

        # Ajouter des recommandations spécifiques basées sur le score
        if score_percentage < 50:
            recommendations.insert(0, "🎯 Priorité: Revoir les fondamentaux de l'IA avant de continuer")
        elif score_percentage < 70:
            recommendations.insert(0, "📚 Consolide tes bases avec des exercices pratiques")
        elif score_percentage >= 90:
            recommendations.insert(0, "🚀 Excellent! Prêt pour des concepts plus avancés")

        # Recommandations basées sur les faiblesses
        if performance["weaknesses"]:
            for weakness in performance["weaknesses"][:2]:
                topic = weakness["topic"]
                recommendations.append(
                    f"🔍 Focus sur {topic}: révise les concepts clés et fais des exercices"
                )

        # 7. Mettre à jour le profil dans la base de données
        update_fields = {
            "xp": new_xp_total,
            "niveau": new_level,
            "current_streak": new_streak,
            "best_streak": max(profile.best_streak, new_streak),
            "last_activity_date": now,
            "quiz_completed": profile.quiz_completed + 1,
            "perfect_quiz_count": profile.perfect_quiz_count + (1 if is_perfect else 0),
            "total_xp_earned": profile.total_xp_earned + xp_earned,
            "updated_at": now,
            "recommandations": recommendations,
        }

        # Ajouter les badges
        if new_badges:
            update_fields["badges"] = list(set(profile.badges + new_badges))

        # Mettre à jour les statistiques détaillées
        stats = profile.statistiques or {}
        stats.update({
            "current_streak": new_streak,
            "quiz_completed": profile.quiz_completed + 1,
            "perfect_quiz_count": profile.perfect_quiz_count + (1 if is_perfect else 0),
            "average_score": (
                (stats.get("average_score", 0) * profile.quiz_completed + score_percentage)
                / (profile.quiz_completed + 1)
            ),
            "last_quiz_score": score_percentage,
            "total_xp_earned": profile.total_xp_earned + xp_earned,
        })

        update_fields["statistiques"] = stats

        # Ajouter l'analyse détaillée
        analyse_detaillee = profile.analyse_detaillee or {}
        quiz_analysis = {
            "timestamp": now,
            "score": score_percentage,
            "questions": total_questions,
            "correct": correct_answers,
            "xp_earned": xp_earned,
            "level": new_level,
            "streak": new_streak,
            "badges_earned": new_badges,
            "performance": performance,
        }

        # Garder seulement les 10 dernières analyses
        analyses_list = list(analyse_detaillee.values()) if isinstance(analyse_detaillee, dict) else []
        analyses_list.append(quiz_analysis)
        analyses_list = analyses_list[-10:]  # Garder seulement les 10 dernières

        # Recréer le dictionnaire avec timestamps comme clés
        update_fields["analyse_detaillee"] = {
            f"quiz_{i}": analysis for i, analysis in enumerate(analyses_list)
        }

        # Appliquer la mise à jour
        await self.collection.update_one(
            {"utilisateur_id": str(user_id)},
            {"$set": update_fields}
        )

        # 8. Logger l'activité
        await self.log_activity(
            user_id,
            "quiz_completed",
            {
                "score": score_percentage,
                "xp_earned": xp_earned,
                "badges_earned": new_badges,
                "level": new_level,
                "streak": new_streak,
            }
        )

        # 9. Récupérer le profil mis à jour
        updated_profile = await self.get_profile_by_user_id(user_id)

        # 10. Retourner le résultat complet
        return {
            "profile": updated_profile,
            "xp_earned": xp_calc,
            "badges_earned": new_badges,
            "level_up": level_up,
            "old_level": old_level,
            "new_level": new_level,
            "streak_info": {
                "current": new_streak,
                "best": max(profile.best_streak, new_streak),
                "is_record": is_new_streak_record,
                "is_active": streak_info["is_active"],
            },
            "quiz_summary": {
                "score": score_percentage,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "is_perfect": is_perfect,
            },
            "performance_analysis": performance,
            "recommendations": recommendations,
        }

    async def save_initial_questionnaire(
        self,
        user_id: UUID,
        questionnaire_data: dict,
        analyse_llm: Optional[Dict[str, Any]] = None
    ) -> ProfilMongoDB:
        """
        Sauvegarde le questionnaire initial de profilage dans MongoDB.

        Ce questionnaire est fait UNE SEULE FOIS pour jauger le niveau réel de l'utilisateur,
        surtout via les questions ouvertes qui révèlent la compréhension profonde.

        Args:
            user_id: UUID de l'utilisateur
            questionnaire_data: Données du questionnaire avec toutes les réponses
            analyse_llm: Analyse optionnelle du LLM sur les questions ouvertes

        Returns:
            ProfilMongoDB mis à jour
        """
        profile = await self.get_profile_by_user_id(user_id)
        if not profile:
            # ✅ Créer automatiquement le profil s'il est manquant
            from src.profile.schema import ProfilCreate
            profil_data = ProfilCreate(
                utilisateur_id=user_id,
                niveau=1,
                xp=0,
                badges=[],
                competences=[],
                energie=5,
                recommandations=[],
                analyse_detaillee={}
            )
            profile = await self.create_profile(profil_data)

        # Vérifier si le questionnaire a déjà été fait
        if profile.questionnaire_initial_complete:
            raise ValueError("Le questionnaire initial a déjà été complété. Il ne peut être fait qu'une seule fois.")

        now = datetime.now()

        # Extraire et structurer les réponses
        questions = questionnaire_data.get("questions_data", []) or questionnaire_data.get("questions", [])

        # Séparer les questions ouvertes des autres
        questions_ouvertes = []
        questions_fermees = []

        for q in questions:
            question_type = q.get("type", "").lower()
            reponse_structure = {
                "question": q.get("question", ""),
                "type": question_type,
                "reponse_utilisateur": q.get("user_answer", ""),
                "timestamp": now.isoformat(),
            }

            if question_type in ["ouverte", "open", "text", "essay"]:
                # Question ouverte - très importante pour l'évaluation
                reponse_structure["poids_evaluation"] = "élevé"  # Plus important pour jauger le niveau
                reponse_structure["correction"] = q.get("correction", "")
                questions_ouvertes.append(reponse_structure)
            else:
                # Question fermée (QCM, Vrai/Faux)
                reponse_structure["poids_evaluation"] = "standard"
                reponse_structure["est_correct"] = q.get("is_correct", False)
                reponse_structure["correction"] = q.get("correction", "")
                questions_fermees.append(reponse_structure)

        # Analyse sémantique des questions ouvertes
        analyse_questions_ouvertes = {
            "nombre_questions_ouvertes": len(questions_ouvertes),
            "questions": questions_ouvertes,
            "analyse_llm": analyse_llm or {},
            "score_global": questionnaire_data.get("score", 0),
            "evaluation_detaillee": {
                "comprehension_profonde": analyse_llm.get("comprehension_profonde", "non_evaluee") if analyse_llm else "non_evaluee",
                "capacite_explication": analyse_llm.get("capacite_explication", "non_evaluee") if analyse_llm else "non_evaluee",
                "niveau_reel_estime": analyse_llm.get("niveau_reel", "non_determine") if analyse_llm else "non_determine",
                "commentaires": analyse_llm.get("commentaires", "") if analyse_llm else "",
            },
            "date_analyse": now.isoformat(),
        }

        # Mettre à jour le profil
        update_fields = {
            "questionnaire_initial_complete": True,
            "questionnaire_initial_date": now,
            "questionnaire_reponses": questions_ouvertes + questions_fermees,  # Toutes les réponses
            "analyse_questions_ouvertes": analyse_questions_ouvertes,
            "updated_at": now,
        }

        # Mettre à jour aussi les compétences et objectifs si fournis
        if analyse_llm:
            competences_identifiees = analyse_llm.get("competences", [])
            if competences_identifiees:
                update_fields["competences"] = list(set(profile.competences + competences_identifiees))

            objectifs_recommandes = analyse_llm.get("objectifs", "")
            if objectifs_recommandes:
                update_fields["objectifs"] = objectifs_recommandes

            motivation = analyse_llm.get("motivation", "")
            if motivation:
                update_fields["motivation"] = motivation

            # Ajouter les recommandations du LLM
            recommandations = analyse_llm.get("recommandations", [])
            if recommandations:
                update_fields["recommandations"] = recommandations

        # Appliquer la mise à jour
        await self.collection.update_one(
            {"utilisateur_id": str(user_id)},
            {"$set": update_fields}
        )

        # Logger l'activité
        await self.log_activity(
            user_id,
            "questionnaire_initial_complete",
            {
                "total_questions": len(questions),
                "questions_ouvertes": len(questions_ouvertes),
                "questions_fermees": len(questions_fermees),
                "score": questionnaire_data.get("score", 0),
                "analyse_disponible": analyse_llm is not None,
            }
        )

        # Récupérer et retourner le profil mis à jour
        updated_profile = await self.get_profile_by_user_id(user_id)
        return updated_profile

    async def has_profile(self, user_id: UUID) -> bool:
        """Retourne True si un profil existe pour cet utilisateur, sinon False (rapide)."""
        result = await self.collection.find_one({"utilisateur_id": str(user_id)}, {"_id": 1})
        return result is not None


# Instance globale du service
profile_service = ProfileService()