"""
Agent de gestion de cours - Gère les cours, modules, roadmaps et ressources.
"""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
from datetime import datetime, timedelta, UTC

from src.config import Config
from src.ai_agents.shared_context import shared_context_service


COURSE_MANAGER_SYSTEM_PROMPT = """
Tu es un architecte pédagogique expert qui conçoit des roadmaps de cours structurées et progressives.

🎯 Ta mission :
Créer des roadmaps de cours détaillées avec :
- Structure modulaire progressive
- Ressources variées (gratuites et payantes)
- Évaluations pour valider la maîtrise
- Estimation de temps réaliste
- Prérequis clairement définis

📚 STRUCTURE D'UN COURS :

1. **Vue d'ensemble**
   - Titre accrocheur
   - Description engageante
   - Objectifs d'apprentissage (SMART)
   - Durée estimée
   - Niveau requis

2. **Modules** (4-8 modules par cours)
   - Progression logique
   - Chaque module = 1 concept clé
   - Durée : 1-3 heures par module

3. **Leçons** (3-6 leçons par module)
   - Théorie (vidéos, articles)
   - Pratique (exercices, code)
   - Quiz de validation

4. **Ressources**
   - 🎥 Vidéos YouTube (gratuites)
   - 📚 Articles et tutoriels
   - 💻 Repositories GitHub
   - 📖 Livres recommandés
   - 🎓 Cours en ligne (Coursera, Udemy, etc.)
   - 🔗 Documentation officielle

5. **Évaluations**
   - Quiz rapides (compréhension)
   - Exercices pratiques (application)
   - Projet de module (intégration)
   - Examen final (maîtrise)

FORMAT JSON STRICT :
{
    "cours": {
        "id": "course_neural_networks_101",
        "titre": "🧠 Les Réseaux de Neurones de A à Z",
        "description": "Maîtrise les fondamentaux des réseaux de neurones...",
        "niveau": "Débutant à Intermédiaire",
        "duree_totale": "6 semaines (10-15h/semaine)",
        "objectifs": [
            "Comprendre l'architecture des réseaux de neurones",
            "Implémenter un réseau from scratch",
            "Entraîner et optimiser un modèle"
        ],
        "prerequis": ["Python de base", "Algèbre linéaire basique"],
        "tags": ["deep-learning", "neural-networks", "python"]
    },
    "roadmap": {
        "progression_type": "linéaire",
        "modules_count": 6,
        "total_lessons": 24,
        "total_exercises": 36,
        "total_projects": 6
    },
    "modules": [
        {
            "id": "module_1",
            "ordre": 1,
            "titre": "🎯 Introduction aux Réseaux de Neurones",
            "description": "Comprends les fondements...",
            "duree_estimee": "1 semaine (10-12h)",
            "objectifs": [
                "Comprendre le neurone artificiel",
                "Implémenter un perceptron"
            ],
            "lecons": [
                {
                    "id": "lesson_1_1",
                    "ordre": 1,
                    "titre": "Le Neurone Artificiel",
                    "type": "theorie",
                    "duree": "45 min",
                    "contenu": {
                        "video_principale": {
                            "titre": "Neural Networks Explained",
                            "url": "https://www.youtube.com/watch?v=aircAruvnKk",
                            "source": "3Blue1Brown",
                            "duree": "19 min",
                            "langue": "EN (sous-titres FR)"
                        },
                        "ressources_complementaires": [
                            {
                                "type": "article",
                                "titre": "Understanding Neural Networks",
                                "url": "https://towardsdatascience.com/...",
                                "gratuit": true
                            }
                        ]
                    }
                },
                {
                    "id": "lesson_1_2",
                    "ordre": 2,
                    "titre": "Implémentation d'un Perceptron",
                    "type": "pratique",
                    "duree": "2h",
                    "exercices": [
                        {
                            "titre": "Perceptron from Scratch",
                            "description": "Implémente un perceptron en Python",
                            "difficulte": "moyen",
                            "temps_estime": "1h30"
                        }
                    ]
                },
                {
                    "id": "lesson_1_3",
                    "ordre": 3,
                    "titre": "Quiz : Les Fondamentaux",
                    "type": "evaluation",
                    "duree": "15 min",
                    "questions_count": 10,
                    "seuil_reussite": 70
                }
            ],
            "projet_module": {
                "titre": "🎯 Projet : Classificateur Binaire",
                "description": "Crée un perceptron qui classifie...",
                "duree_estimee": "3-4h",
                "criteres_validation": [
                    "Implémentation correcte",
                    "Précision > 85%",
                    "Code commenté"
                ],
                "ressources": [
                    {
                        "type": "dataset",
                        "nom": "Iris Dataset",
                        "url": "https://..."
                    }
                ]
            },
            "evaluation_module": {
                "type": "quiz_pratique",
                "questions": 15,
                "duree": "30 min",
                "seuil_reussite": 75,
                "debloquer_module_suivant": true
            }
        }
    ],
    "ressources_globales": {
        "livres": [
            {
                "titre": "Deep Learning with Python",
                "auteur": "François Chollet",
                "gratuit": false,
                "prix": "~40€",
                "url": "https://..."
            }
        ],
        "cours_en_ligne": [
            {
                "titre": "Deep Learning Specialization",
                "plateforme": "Coursera",
                "gratuit": "audit gratuit",
                "certification": "payante",
                "url": "https://..."
            }
        ],
        "outils": [
            {
                "nom": "Google Colab",
                "description": "Notebooks gratuits avec GPU",
                "url": "https://colab.research.google.com",
                "gratuit": true
            }
        ],
        "communautes": [
            {
                "nom": "r/MachineLearning",
                "type": "Reddit",
                "url": "https://reddit.com/r/MachineLearning"
            }
        ]
    },
    "evaluation_finale": {
        "titre": "🏆 Projet Final : Votre Premier Réseau de Neurones",
        "description": "Crée un réseau complet qui résout un problème réel",
        "duree_estimee": "2 semaines",
        "validation_niveau": true,
        "badge": "Neural Network Master"
    }
}
"""


class CourseManagerAgent:
    """
    Agent de gestion de cours et création de roadmaps détaillées.
    Intègre des ressources du web et structure l'apprentissage.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.6  # Balance créativité et structure
        )
        self.name = "CourseManagerAgent"

    async def create_course_roadmap(
        self,
        course_topic: str,
        user_level: int,
        user_objectives: str,
        duration_weeks: int = 6
    ) -> Dict[str, Any]:
        """
        Créer une roadmap de cours complète avec ressources.

        Args:
            course_topic: Sujet du cours
            user_level: Niveau de l'utilisateur (1-10)
            user_objectives: Objectifs de l'utilisateur
            duration_weeks: Durée souhaitée en semaines

        Returns:
            Roadmap complète du cours
        """
        try:
            messages = [
                SystemMessage(content=COURSE_MANAGER_SYSTEM_PROMPT),
                HumanMessage(content=f"""
Crée une roadmap de cours complète pour :

📚 SUJET : {course_topic}
👤 NIVEAU UTILISATEUR : {user_level}/10
🎯 OBJECTIFS : {user_objectives}
⏰ DURÉE : {duration_weeks} semaines

⚠️ CONTRAINTES IMPORTANTES :
1. Ressources RÉELLES et accessibles (YouTube, articles, GitHub)
2. Mix gratuit/payant avec priorité au gratuit
3. Progression adaptée au niveau {user_level}
4. Évaluations à chaque module
5. Projet pratique par module
6. Estimation de temps RÉALISTE

🎯 STRUCTURE ATTENDUE :
- {duration_weeks} modules (1 par semaine)
- 3-5 leçons par module
- Mix théorie/pratique (40/60)
- Ressources variées et de qualité
- Évaluations progressives

Génère maintenant la roadmap complète en JSON.
                """)
            ]

            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parser JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            roadmap = json.loads(response_text)

            # Ajouter métadonnées
            roadmap["meta"] = {
                "created_at": datetime.now(UTC).isoformat(),
                "user_level": user_level,
                "estimated_completion_date": (
                    datetime.now(UTC) + timedelta(weeks=duration_weeks)
                ).isoformat(),
                "total_modules": len(roadmap.get("modules", [])),
                "generated_by": self.name
            }

            return roadmap

        except Exception as e:
            raise Exception(f"Erreur création roadmap: {str(e)}")

    async def get_next_module(
        self,
        user_id: str,
        course_id: str,
        current_progress: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Obtenir le prochain module à étudier.
        """
        # Logique de sélection du prochain module basée sur la progression
        completed_modules = current_progress.get("completed_modules", [])

        # TODO: Récupérer le cours depuis MongoDB
        # Pour l'instant, retourner un module exemple

        return {
            "module_id": "next_module",
            "titre": "Prochain module à débloquer",
            "status": "locked" if len(completed_modules) < 1 else "available"
        }

    async def validate_module_completion(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        evaluation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valider la complétion d'un module basé sur l'évaluation.

        Args:
            user_id: ID utilisateur
            session_id: ID de session
            module_id: ID du module
            evaluation_results: Résultats de l'évaluation

        Returns:
            Validation et déblocage du module suivant
        """
        try:
            score = evaluation_results.get("score", 0)
            seuil = evaluation_results.get("seuil_reussite", 70)

            passed = score >= seuil

            if passed:
                # Débloquer le module suivant
                await shared_context_service.add_message(
                    user_id,
                    session_id,
                    self.name,
                    f"Module {module_id} validé avec {score}% ! Module suivant débloqué. 🎉"
                )

                return {
                    "module_completed": True,
                    "score": score,
                    "next_module_unlocked": True,
                    "badge_earned": f"Module {module_id} Master",
                    "xp_gained": 200
                }
            else:
                # Suggérer de réviser
                await shared_context_service.add_message(
                    user_id,
                    session_id,
                    self.name,
                    f"Score de {score}% au module {module_id}. Révise les concepts clés et retente ! 💪"
                )

                return {
                    "module_completed": False,
                    "score": score,
                    "retry_recommended": True,
                    "weak_areas": evaluation_results.get("weak_areas", [])
                }

        except Exception as e:
            return {
                "error": str(e),
                "module_completed": False
            }

    async def recommend_resources(
        self,
        topic: str,
        user_level: int,
        resource_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Recommander des ressources pour un sujet.
        Utilise MCP pour rechercher des ressources réelles sur le web.
        """
        try:
            # TODO: Intégrer MCP pour recherche web réelle
            # Pour l'instant, retourner des ressources génériques

            resources = []

            if resource_type in ["all", "video"]:
                resources.extend([
                    {
                        "type": "video",
                        "titre": f"Introduction à {topic}",
                        "plateforme": "YouTube",
                        "gratuit": True,
                        "niveau": user_level,
                        "url": f"https://youtube.com/search?q={topic.replace(' ', '+')}"
                    }
                ])

            if resource_type in ["all", "article"]:
                resources.extend([
                    {
                        "type": "article",
                        "titre": f"Guide complet : {topic}",
                        "source": "Medium/Towards Data Science",
                        "gratuit": True,
                        "niveau": user_level
                    }
                ])

            if resource_type in ["all", "course"]:
                resources.extend([
                    {
                        "type": "course",
                        "titre": f"Cours {topic}",
                        "plateforme": "Coursera",
                        "gratuit": "Audit gratuit",
                        "certification": "Payante",
                        "niveau": user_level
                    }
                ])

            return resources

        except Exception as e:
            print(f"Erreur recommandation ressources: {e}")
            return []


# Instance globale
course_manager_agent = CourseManagerAgent()

