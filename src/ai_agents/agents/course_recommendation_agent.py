"""
Agent de recommandation de ressources avec MCP (Model Context Protocol).
Recherche et recommande des cours gratuits sur YouTube, Coursera, edX, etc.
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import httpx
from urllib.parse import quote_plus

from src.config import Config


RECOMMENDATION_SYSTEM_PROMPT = """
Tu es un expert en curation de ressources d'apprentissage en Intelligence Artificielle.

🎯 Ta mission :
Recommander les MEILLEURES ressources gratuites adaptées au niveau et objectifs de l'apprenant.

📊 Critères de sélection :
1. **Qualité** : Notation élevée, contenu reconnu
2. **Gratuité** : Priorité aux ressources 100% gratuites
3. **Langue** : Priorité français, puis anglais avec sous-titres
4. **Actualité** : Contenu récent (sauf classiques intemporels)
5. **Progression** : Adapté au niveau actuel

🎓 Types de ressources :
- 📹 **Vidéos YouTube** : Tutoriels, explications visuelles
- 🎓 **Cours en ligne** : Coursera, edX, Khan Academy, OpenClassrooms
- 📚 **Articles/Tutoriels** : Medium, Towards Data Science, blogs experts
- 💻 **Code/Projets** : GitHub, Kaggle, Google Colab
- 📖 **Documentation** : TensorFlow, PyTorch, scikit-learn

🏆 Sources prioritaires :
- **YouTube** : 3Blue1Brown, Yannic Kilcher, Sentdex, Machine Learnia (FR)
- **Coursera** : Andrew Ng, deeplearning.ai
- **edX** : MIT, Stanford
- **Kaggle** : Notebooks, compétitions pour débutants
- **Papers with Code** : Papiers de recherche + implémentations

FORMAT JSON STRICT :
{
  "ressources_recommandees": [
    {
      "titre": "Titre accrocheur",
      "url": "https://...",
      "type": "video|cours|article|code|doc",
      "plateforme": "YouTube|Coursera|edX|...",
      "auteur": "Nom auteur/créateur",
      "duree_estimee": "2h30",
      "gratuit": true,
      "langue": "fr|en",
      "sous_titres_fr": true,
      "niveau_requis": "débutant|intermédiaire|avancé",
      "note_qualite": 9.2,
      "description": "Courte description...",
      "pourquoi_recommande": "Raison personnalisée pour cet apprenant"
    }
  ],
  "roadmap_suggeree": [
    {
      "etape": 1,
      "titre": "Fondamentaux",
      "ressources": ["ressource_1", "ressource_2"],
      "duree_totale": "10h",
      "objectif": "Maîtriser les bases du ML"
    }
  ],
  "projets_pratiques": [
    {
      "titre": "Mini-projet : Classification d'images",
      "difficulte": "facile",
      "duree": "3h",
      "lien_starter": "https://github.com/...",
      "description": "..."
    }
  ]
}
"""


class CourseRecommendationAgent:
    """Agent de recommandation avec recherche web (MCP)."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.5
        )
        self.name = "CourseRecommendationAgent"

    async def search_youtube_videos(
        self,
        topic: str,
        language: str = "fr",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche des vidéos YouTube pertinentes.

        Args:
            topic: Sujet à rechercher
            language: Langue préférée
            max_results: Nombre maximum de résultats

        Returns:
            Liste de vidéos avec métadonnées
        """
        # Note: Pour une vraie implémentation, utiliser YouTube Data API v3
        # Ici, simulation avec recherche Google Custom Search API

        query = f"{topic} tutoriel {language} machine learning"

        # Pour l'instant, retourner des recommandations fixes de qualité
        # TODO: Intégrer YouTube Data API

        if language == "fr":
            videos = [
                {
                    "titre": "Machine Learning pour Débutants - Série complète",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder
                    "auteur": "Machine Learnia",
                    "duree": "2h30",
                    "plateforme": "YouTube",
                    "langue": "fr",
                    "description": "Introduction complète au ML en français"
                },
                {
                    "titre": "Les Réseaux de Neurones Expliqués Visuellement",
                    "url": "https://www.youtube.com/c/3blue1brown",
                    "auteur": "3Blue1Brown",
                    "duree": "1h45",
                    "plateforme": "YouTube",
                    "langue": "en",
                    "sous_titres_fr": True,
                    "description": "Visualisations exceptionnelles des concepts ML"
                }
            ]
        else:
            videos = [
                {
                    "titre": "Neural Networks from Scratch",
                    "url": "https://www.youtube.com/sentdex",
                    "auteur": "Sentdex",
                    "duree": "3h",
                    "plateforme": "YouTube",
                    "langue": "en",
                    "description": "Implémentation complète from scratch"
                }
            ]

        return videos[:max_results]

    async def search_online_courses(
        self,
        topic: str,
        free_only: bool = True,
        platforms: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche des cours en ligne sur Coursera, edX, etc.

        Args:
            topic: Sujet à rechercher
            free_only: Uniquement cours gratuits
            platforms: Liste des plateformes à chercher

        Returns:
            Liste de cours avec métadonnées
        """
        platforms = platforms or ["coursera", "edx", "openclassrooms", "khan_academy"]

        # Cours de référence (base de données fixe pour l'instant)
        # TODO: Intégrer APIs des plateformes

        courses = [
            {
                "titre": "Machine Learning par Andrew Ng",
                "url": "https://www.coursera.org/learn/machine-learning",
                "plateforme": "Coursera",
                "auteur": "Andrew Ng (Stanford)",
                "duree": "60h",
                "gratuit": True,  # Audit gratuit
                "certification_payante": True,
                "langue": "en",
                "sous_titres_fr": True,
                "niveau": "débutant",
                "note": 4.9,
                "description": "LE cours de référence en Machine Learning"
            },
            {
                "titre": "Deep Learning Specialization",
                "url": "https://www.coursera.org/specializations/deep-learning",
                "plateforme": "Coursera",
                "auteur": "deeplearning.ai",
                "duree": "120h",
                "gratuit": True,  # Audit
                "niveau": "intermédiaire",
                "note": 4.8,
                "description": "5 cours sur le Deep Learning"
            },
            {
                "titre": "Initiez-vous au Machine Learning",
                "url": "https://openclassrooms.com/fr/courses/4011851",
                "plateforme": "OpenClassrooms",
                "auteur": "OpenClassrooms",
                "duree": "10h",
                "gratuit": True,
                "langue": "fr",
                "niveau": "débutant",
                "description": "Introduction en français au ML"
            }
        ]

        # Filtrer selon free_only
        if free_only:
            courses = [c for c in courses if c["gratuit"]]

        return courses

    async def search_github_projects(
        self,
        topic: str,
        difficulty: str = "beginner"
    ) -> List[Dict[str, Any]]:
        """
        Recherche des projets GitHub éducatifs.

        Args:
            topic: Sujet (ex: "classification", "nlp")
            difficulty: Niveau (beginner, intermediate, advanced)

        Returns:
            Liste de projets GitHub
        """
        # Projets de référence classés par difficulté
        projects = {
            "beginner": [
                {
                    "titre": "ML From Scratch",
                    "url": "https://github.com/eriklindernoren/ML-From-Scratch",
                    "stars": "20k+",
                    "description": "Implémentations ML from scratch en Python",
                    "technologies": ["Python", "NumPy"],
                    "ideal_pour": "Comprendre les algorithmes en profondeur"
                },
                {
                    "titre": "100 Days of ML Code",
                    "url": "https://github.com/Avik-Jain/100-Days-Of-ML-Code",
                    "stars": "40k+",
                    "description": "Défi 100 jours avec tutoriels quotidiens",
                    "ideal_pour": "Apprendre progressivement"
                }
            ],
            "intermediate": [
                {
                    "titre": "Keras Examples",
                    "url": "https://github.com/keras-team/keras-io",
                    "stars": "10k+",
                    "description": "Exemples pratiques avec Keras",
                    "technologies": ["Python", "TensorFlow", "Keras"]
                }
            ],
            "advanced": [
                {
                    "titre": "Papers with Code",
                    "url": "https://github.com/paperswithcode",
                    "description": "Implémentations de papiers de recherche",
                    "ideal_pour": "Explorer l'état de l'art"
                }
            ]
        }

        return projects.get(difficulty, projects["beginner"])

    async def create_learning_roadmap(
        self,
        user_level: int,
        user_objectives: str,
        user_competences: List[str],
        duration_weeks: int = 12
    ) -> Dict[str, Any]:
        """
        Crée une roadmap personnalisée avec ressources gratuites.

        Args:
            user_level: Niveau actuel (1-10)
            user_objectives: Objectifs d'apprentissage
            user_competences: Compétences actuelles
            duration_weeks: Durée souhaitée en semaines

        Returns:
            Roadmap complète avec ressources pour chaque étape
        """
        context = f"""
PROFIL APPRENANT :
- Niveau actuel : {user_level}/10
- Compétences : {', '.join(user_competences) if user_competences else 'Aucune'}
- Objectifs : {user_objectives}
- Durée souhaitée : {duration_weeks} semaines
"""

        messages = [
            SystemMessage(content=RECOMMENDATION_SYSTEM_PROMPT),
            HumanMessage(content=f"""
{context}

Crée une roadmap d'apprentissage personnalisée sur {duration_weeks} semaines.

Pour chaque étape, fournis :
- Objectif pédagogique clair
- Liste de ressources gratuites recommandées (YouTube, Coursera, GitHub)
- Durée estimée
- Critères de validation (comment savoir qu'on maîtrise ?)
- Mini-projet pratique

Privilégie les ressources :
- 100% gratuites
- En français quand possible (sinon anglais avec sous-titres)
- De haute qualité (Andrew Ng, 3Blue1Brown, Machine Learnia, etc.)
- Avec exercices pratiques

Retourne un JSON structuré.
            """)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            roadmap = json.loads(response_text)

            # Enrichir avec recherches réelles
            youtube_videos = await self.search_youtube_videos(user_objectives)
            online_courses = await self.search_online_courses(user_objectives)
            github_projects = await self.search_github_projects(user_objectives)

            roadmap["ressources_supplementaires"] = {
                "videos_youtube": youtube_videos,
                "cours_en_ligne": online_courses,
                "projets_github": github_projects
            }

            return roadmap

        except Exception as e:
            print(f"❌ Erreur création roadmap: {e}")
            return {
                "error": str(e),
                "roadmap_suggeree": [],
                "ressources_recommandees": []
            }

    async def recommend(self, state: Any) -> Dict[str, Any]:
        """
        Point d'entrée du workflow pour les recommandations.

        Args:
            state: État actuel

        Returns:
            Recommandations et roadmap
        """
        user_level = state.get("user_level", 5)
        user_objectives = state.get("user_objectifs", "")
        user_competences = state.get("user_competences", [])

        # Créer la roadmap personnalisée
        roadmap = await self.create_learning_roadmap(
            user_level=user_level,
            user_objectives=user_objectives,
            user_competences=user_competences,
            duration_weeks=12
        )

        return {
            "learning_roadmap": roadmap,
            "current_step": "recommendation_complete",
            "next_step": "end"
        }


# Instance globale
course_recommendation_agent = CourseRecommendationAgent()

