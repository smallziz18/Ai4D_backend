"""
Système de gamification complet pour l'apprentissage de l'IA
Inspiré de boot.dev avec badges, streaks, achievements, et XP
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


# Système de niveaux détaillé (1-10)
LEVEL_SYSTEM = {
    1: {"label": "Novice", "xp_min": 0, "xp_max": 100, "description": "Découverte de l'IA"},
    2: {"label": "Débutant", "xp_min": 100, "xp_max": 300, "description": "Apprentissage des bases"},
    3: {"label": "Apprenti", "xp_min": 300, "xp_max": 600, "description": "Compréhension des concepts fondamentaux"},
    4: {"label": "Initié", "xp_min": 600, "xp_max": 1000, "description": "Maîtrise des fondamentaux"},
    5: {"label": "Intermédiaire", "xp_min": 1000, "xp_max": 1500, "description": "Application pratique"},
    6: {"label": "Confirmé", "xp_min": 1500, "xp_max": 2200, "description": "Projets complexes"},
    7: {"label": "Avancé", "xp_min": 2200, "xp_max": 3000, "description": "Expertise technique"},
    8: {"label": "Expert", "xp_min": 3000, "xp_max": 4000, "description": "Maîtrise approfondie"},
    9: {"label": "Maître", "xp_min": 4000, "xp_max": 5500, "description": "Innovation et recherche"},
    10: {"label": "Grand Maître", "xp_min": 5500, "xp_max": float('inf'), "description": "Niveau élite"}
}


class BadgeCategory(str, Enum):
    """Catégories de badges"""
    STREAK = "streak"  # Séries de jours consécutifs
    MASTERY = "mastery"  # Maîtrise d'un domaine
    ACHIEVEMENT = "achievement"  # Succès spéciaux
    LEVEL = "level"  # Paliers de niveau
    SOCIAL = "social"  # Interactions sociales


class Achievement(str, Enum):
    """Achievements débloquables"""
    # Débuts
    FIRST_QUIZ = "first_quiz"
    FIRST_PERFECT = "first_perfect"
    FIRST_WEEK = "first_week"

    # Streaks
    STREAK_3 = "streak_3_days"
    STREAK_7 = "streak_7_days"
    STREAK_30 = "streak_30_days"
    STREAK_100 = "streak_100_days"

    # Maîtrise
    ML_BASICS = "ml_basics_master"
    DEEP_LEARNING = "deep_learning_master"
    NLP_EXPERT = "nlp_expert"
    COMPUTER_VISION = "computer_vision_expert"

    # Niveaux
    LEVEL_5 = "level_5_reached"
    LEVEL_10 = "level_10_reached"
    LEVEL_25 = "level_25_reached"
    LEVEL_50 = "level_50_reached"

    # Spéciaux
    NIGHT_OWL = "night_owl"  # Compléter un quiz après minuit
    EARLY_BIRD = "early_bird"  # Compléter un quiz avant 6h
    SPEED_DEMON = "speed_demon"  # Compléter un quiz en moins de 5 minutes
    PERFECTIONIST = "perfectionist"  # 10 quiz parfaits d'affilée


# Configuration des badges avec métadonnées
BADGE_CONFIG = {
    # Streaks
    "🔥 Habitué": {
        "category": BadgeCategory.STREAK,
        "description": "3 jours consécutifs d'apprentissage",
        "xp_reward": 50,
        "condition": "streak >= 3"
    },
    "🔥 Assidu": {
        "category": BadgeCategory.STREAK,
        "description": "7 jours consécutifs d'apprentissage",
        "xp_reward": 150,
        "condition": "streak >= 7"
    },
    "🔥 Dédié": {
        "category": BadgeCategory.STREAK,
        "description": "30 jours consécutifs d'apprentissage",
        "xp_reward": 500,
        "condition": "streak >= 30"
    },
    "🔥 Légende": {
        "category": BadgeCategory.STREAK,
        "description": "100 jours consécutifs d'apprentissage",
        "xp_reward": 2000,
        "condition": "streak >= 100"
    },

    # Maîtrise par domaine
    "🧠 ML Fondamentaux": {
        "category": BadgeCategory.MASTERY,
        "description": "Maîtrise des concepts de base du Machine Learning",
        "xp_reward": 300,
        "condition": "ml_basics_score >= 90"
    },
    "🤖 Deep Learning Expert": {
        "category": BadgeCategory.MASTERY,
        "description": "Expertise en Deep Learning et réseaux de neurones",
        "xp_reward": 500,
        "condition": "deep_learning_score >= 90"
    },
    "💬 NLP Maître": {
        "category": BadgeCategory.MASTERY,
        "description": "Maîtrise du Natural Language Processing",
        "xp_reward": 500,
        "condition": "nlp_score >= 90"
    },
    "👁️ Computer Vision Pro": {
        "category": BadgeCategory.MASTERY,
        "description": "Expert en traitement d'images et Computer Vision",
        "xp_reward": 500,
        "condition": "cv_score >= 90"
    },

    # Niveaux (système 1-10)
    "⭐ Novice": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 1 - Premiers pas en IA",
        "xp_reward": 50,
        "condition": "level >= 1"
    },
    "⭐ Débutant": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 2 - Bases de l'IA acquises",
        "xp_reward": 75,
        "condition": "level >= 2"
    },
    "⭐⭐ Apprenti": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 3 - Concepts fondamentaux maîtrisés",
        "xp_reward": 100,
        "condition": "level >= 3"
    },
    "⭐⭐ Initié": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 4 - Fondamentaux solides",
        "xp_reward": 150,
        "condition": "level >= 4"
    },
    "⭐⭐⭐ Intermédiaire": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 5 - Application pratique",
        "xp_reward": 300,
        "condition": "level >= 5"
    },
    "⭐⭐⭐ Confirmé": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 6 - Projets complexes",
        "xp_reward": 500,
        "condition": "level >= 6"
    },
    "⭐⭐⭐⭐ Avancé": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 7 - Expertise technique",
        "xp_reward": 800,
        "condition": "level >= 7"
    },
    "⭐⭐⭐⭐ Expert": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 8 - Maîtrise approfondie",
        "xp_reward": 1200,
        "condition": "level >= 8"
    },
    "👑 Maître": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 9 - Innovation et recherche",
        "xp_reward": 2000,
        "condition": "level >= 9"
    },
    "👑 Grand Maître": {
        "category": BadgeCategory.LEVEL,
        "description": "Niveau 10 - Niveau élite atteint",
        "xp_reward": 5000,
        "condition": "level >= 10"
    },

    # Achievements spéciaux
    "🎯 Premier Pas": {
        "category": BadgeCategory.ACHIEVEMENT,
        "description": "Premier quiz complété",
        "xp_reward": 50,
        "condition": "quiz_count >= 1"
    },
    "💯 Perfectionniste": {
        "category": BadgeCategory.ACHIEVEMENT,
        "description": "Score parfait (100%) sur un quiz",
        "xp_reward": 200,
        "condition": "perfect_quiz_count >= 1"
    },
    "🦉 Oiseau de Nuit": {
        "category": BadgeCategory.ACHIEVEMENT,
        "description": "Quiz complété après minuit",
        "xp_reward": 100,
        "condition": "night_quiz_count >= 1"
    },
    "🌅 Lève-tôt": {
        "category": BadgeCategory.ACHIEVEMENT,
        "description": "Quiz complété avant 6h du matin",
        "xp_reward": 100,
        "condition": "early_quiz_count >= 1"
    },
    "⚡ Rapide": {
        "category": BadgeCategory.ACHIEVEMENT,
        "description": "Quiz complété en moins de 5 minutes",
        "xp_reward": 150,
        "condition": "speed_quiz_count >= 1"
    },
}


# Configuration XP par action
XP_REWARDS = {
    "quiz_completed": 100,
    "quiz_perfect": 300,  # Bonus pour 100%
    "question_correct": 10,
    "question_correct_hard": 25,  # Questions difficiles
    "daily_streak": 50,  # Bonus quotidien pour la streak
    "first_quiz_of_day": 25,
    "level_up": 500,
    "badge_earned": 100,
}


# Multiplicateurs XP
XP_MULTIPLIERS = {
    "streak_3": 1.1,  # +10% XP avec 3+ jours de streak
    "streak_7": 1.25,  # +25% XP avec 7+ jours de streak
    "streak_30": 1.5,  # +50% XP avec 30+ jours de streak
    "night_owl": 1.2,  # +20% XP pour quiz de nuit
    "speed_bonus": 1.15,  # +15% XP pour quiz rapides
}


class GamificationEngine:
    """Moteur de gamification pour calculer XP, badges, et streaks"""

    @staticmethod
    def calculate_quiz_xp(
        score_percentage: float,
        total_questions: int,
        correct_answers: int,
        time_taken_seconds: Optional[int] = None,
        current_streak: int = 0,
        quiz_hour: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calcule l'XP gagné pour un quiz avec tous les bonus

        Returns:
            {
                "base_xp": int,
                "bonus_xp": int,
                "total_xp": int,
                "multiplier": float,
                "breakdown": {...}
            }
        """
        breakdown = {}

        # XP de base
        base_xp = XP_REWARDS["quiz_completed"]
        breakdown["quiz_completed"] = base_xp

        # XP par question correcte
        question_xp = correct_answers * XP_REWARDS["question_correct"]
        breakdown["correct_answers"] = question_xp

        # Bonus pour score parfait
        perfect_bonus = 0
        if score_percentage >= 100:
            perfect_bonus = XP_REWARDS["quiz_perfect"]
            breakdown["perfect_score"] = perfect_bonus

        # Bonus pour score élevé
        high_score_bonus = 0
        if 90 <= score_percentage < 100:
            high_score_bonus = 150
            breakdown["high_score"] = high_score_bonus
        elif 80 <= score_percentage < 90:
            high_score_bonus = 75
            breakdown["good_score"] = high_score_bonus

        # Calculer XP total avant multiplicateurs
        total_before_multiplier = base_xp + question_xp + perfect_bonus + high_score_bonus

        # Appliquer les multiplicateurs
        multiplier = 1.0
        multiplier_details = {}

        # Multiplicateur de streak
        if current_streak >= 30:
            multiplier *= XP_MULTIPLIERS["streak_30"]
            multiplier_details["streak_30"] = XP_MULTIPLIERS["streak_30"]
        elif current_streak >= 7:
            multiplier *= XP_MULTIPLIERS["streak_7"]
            multiplier_details["streak_7"] = XP_MULTIPLIERS["streak_7"]
        elif current_streak >= 3:
            multiplier *= XP_MULTIPLIERS["streak_3"]
            multiplier_details["streak_3"] = XP_MULTIPLIERS["streak_3"]

        # Multiplicateur de vitesse (quiz complété en moins de 5 minutes)
        if time_taken_seconds and time_taken_seconds < 300:
            multiplier *= XP_MULTIPLIERS["speed_bonus"]
            multiplier_details["speed_bonus"] = XP_MULTIPLIERS["speed_bonus"]

        # Multiplicateur de nuit (entre minuit et 6h)
        if quiz_hour is not None and (quiz_hour >= 0 and quiz_hour < 6):
            multiplier *= XP_MULTIPLIERS["night_owl"]
            multiplier_details["night_owl"] = XP_MULTIPLIERS["night_owl"]

        # XP final avec multiplicateurs
        bonus_xp = int(total_before_multiplier * (multiplier - 1.0))
        total_xp = int(total_before_multiplier * multiplier)

        return {
            "base_xp": total_before_multiplier,
            "bonus_xp": bonus_xp,
            "total_xp": total_xp,
            "multiplier": round(multiplier, 2),
            "breakdown": breakdown,
            "multiplier_details": multiplier_details
        }

    @staticmethod
    def calculate_level(xp: int) -> int:
        """Calcule le niveau basé sur l'XP total (progression exponentielle)"""
        # Formule: niveau = floor(sqrt(xp / 100))
        # Niveau 1 = 0 XP
        # Niveau 2 = 100 XP
        # Niveau 5 = 2500 XP
        # Niveau 10 = 10000 XP
        # Niveau 25 = 62500 XP
        # Niveau 50 = 250000 XP
        import math
        if xp <= 0:
            return 1
        level = int(math.sqrt(xp / 100)) + 1
        return max(1, level)

    @staticmethod
    def xp_for_next_level(current_level: int) -> int:
        """Calcule l'XP nécessaire pour atteindre le niveau suivant"""
        # XP requis pour niveau N = (N-1)^2 * 100
        return ((current_level) ** 2) * 100

    @staticmethod
    def calculate_streak(last_activity_date: Optional[datetime], current_streak: int = 0) -> Dict[str, Any]:
        """
        Calcule la streak actuelle

        Returns:
            {
                "current_streak": int,
                "is_active": bool,
                "streak_broken": bool,
                "days_since_last": int
            }
        """
        if not last_activity_date:
            return {
                "current_streak": 0,
                "is_active": False,
                "streak_broken": False,
                "days_since_last": None
            }

        now = datetime.now()
        today = now.date()
        last_date = last_activity_date.date()

        days_diff = (today - last_date).days

        if days_diff == 0:
            # Activité aujourd'hui, streak continue
            return {
                "current_streak": current_streak,
                "is_active": True,
                "streak_broken": False,
                "days_since_last": 0
            }
        elif days_diff == 1:
            # Activité hier, incrémenter la streak
            return {
                "current_streak": current_streak + 1,
                "is_active": True,
                "streak_broken": False,
                "days_since_last": 1
            }
        else:
            # Streak cassée
            return {
                "current_streak": 0,
                "is_active": False,
                "streak_broken": True,
                "days_since_last": days_diff
            }

    @staticmethod
    def check_new_badges(profile_data: Dict[str, Any], quiz_result: Dict[str, Any]) -> List[str]:
        """
        Vérifie quels nouveaux badges peuvent être débloqués

        Returns:
            Liste des noms de badges nouvellement débloqués
        """
        current_badges = profile_data.get("badges", [])
        new_badges = []

        # Extraire les données du profil
        level = profile_data.get("niveau", 1)
        streak = profile_data.get("statistiques", {}).get("current_streak", 0)
        quiz_count = profile_data.get("statistiques", {}).get("quiz_completed", 0)
        perfect_count = profile_data.get("statistiques", {}).get("perfect_quiz_count", 0)

        # Extraire les données du quiz
        score = quiz_result.get("score_percentage", 0)
        quiz_time = quiz_result.get("completed_at")

        # Vérifier chaque badge
        for badge_name, config in BADGE_CONFIG.items():
            if badge_name in current_badges:
                continue  # Badge déjà obtenu

            # Vérifier la condition
            condition = config.get("condition", "")

            # Évaluer la condition (simplifiée)
            should_award = False

            # Streaks
            if "streak >= 3" in condition and streak >= 3:
                should_award = True
            elif "streak >= 7" in condition and streak >= 7:
                should_award = True
            elif "streak >= 30" in condition and streak >= 30:
                should_award = True
            elif "streak >= 100" in condition and streak >= 100:
                should_award = True

            # Niveaux
            elif "level >= 5" in condition and level >= 5:
                should_award = True
            elif "level >= 10" in condition and level >= 10:
                should_award = True
            elif "level >= 25" in condition and level >= 25:
                should_award = True
            elif "level >= 50" in condition and level >= 50:
                should_award = True

            # Quiz
            elif "quiz_count >= 1" in condition and quiz_count >= 1:
                should_award = True
            elif "perfect_quiz_count >= 1" in condition and perfect_count >= 1:
                should_award = True

            # Horaires
            elif "night_quiz_count >= 1" in condition and quiz_time:
                hour = quiz_time.hour if isinstance(quiz_time, datetime) else None
                if hour and (hour >= 0 and hour < 6):
                    should_award = True
            elif "early_quiz_count >= 1" in condition and quiz_time:
                hour = quiz_time.hour if isinstance(quiz_time, datetime) else None
                if hour and (hour >= 0 and hour < 6):
                    should_award = True

            if should_award:
                new_badges.append(badge_name)

        return new_badges

    @staticmethod
    def analyze_quiz_performance(questions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyse détaillée de la performance au quiz

        Returns:
            {
                "strengths": [...],  # Domaines maîtrisés
                "weaknesses": [...],  # Domaines à améliorer
                "by_type": {...},  # Performance par type de question
                "by_topic": {...},  # Performance par sujet
                "recommendations": [...]  # Recommandations personnalisées
            }
        """
        strengths = []
        weaknesses = []
        by_type = {}
        by_topic = {}

        for q in questions_data:
            qtype = q.get("type", "Unknown")
            topic = q.get("topic", "Général")
            is_correct = q.get("is_correct", False)

            # Par type
            if qtype not in by_type:
                by_type[qtype] = {"total": 0, "correct": 0}
            by_type[qtype]["total"] += 1
            if is_correct:
                by_type[qtype]["correct"] += 1

            # Par sujet
            if topic not in by_topic:
                by_topic[topic] = {"total": 0, "correct": 0}
            by_topic[topic]["total"] += 1
            if is_correct:
                by_topic[topic]["correct"] += 1

        # Identifier forces et faiblesses
        for topic, stats in by_topic.items():
            if stats["total"] == 0:
                continue
            score = (stats["correct"] / stats["total"]) * 100
            if score >= 80:
                strengths.append({
                    "topic": topic,
                    "score": round(score, 1),
                    "questions": stats["total"]
                })
            elif score < 50:
                weaknesses.append({
                    "topic": topic,
                    "score": round(score, 1),
                    "questions": stats["total"]
                })

        # Générer recommandations
        recommendations = []
        if weaknesses:
            for w in weaknesses[:3]:  # Top 3 faiblesses
                recommendations.append(
                    f"Renforcer {w['topic']} (score actuel: {w['score']}%)"
                )

        if strengths:
            recommendations.append(
                f"Excellent travail sur {strengths[0]['topic']} ! Continue comme ça."
            )

        # Performance par type de question
        for qtype, stats in by_type.items():
            if stats["total"] == 0:
                continue
            score = (stats["correct"] / stats["total"]) * 100
            if score < 60:
                recommendations.append(
                    f"Pratique davantage les questions de type '{qtype}'"
                )

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "by_type": by_type,
            "by_topic": by_topic,
            "recommendations": recommendations
        }


# Fonction utilitaire pour formater l'affichage du profil
def format_profile_display(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Formate les données du profil pour l'affichage utilisateur"""
    niveau = profile.get("niveau", 1)
    xp = profile.get("xp", 0)

    xp_needed = GamificationEngine.xp_for_next_level(niveau)
    xp_current_level = ((niveau - 1) ** 2) * 100 if niveau > 1 else 0
    xp_progress = xp - xp_current_level
    xp_for_next = xp_needed - xp_current_level
    progress_percentage = (xp_progress / xp_for_next * 100) if xp_for_next > 0 else 0

    stats = profile.get("statistiques", {})

    return {
        "niveau": niveau,
        "xp_total": xp,
        "xp_actuel": xp_progress,
        "xp_prochain_niveau": xp_for_next,
        "progression_pourcentage": round(progress_percentage, 1),
        "badges": profile.get("badges", []),
        "nombre_badges": len(profile.get("badges", [])),
        "streak_actuelle": stats.get("current_streak", 0),
        "meilleure_streak": stats.get("best_streak", 0),
        "quiz_completes": stats.get("quiz_completed", 0),
        "score_moyen": round(stats.get("average_score", 0), 1),
        "classement": profile.get("rank"),
    }

