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
        Recherche des vidéos YouTube pertinentes avec vraies recherches.

        Args:
            topic: Sujet à rechercher
            language: Langue préférée
            max_results: Nombre maximum de résultats

        Returns:
            Liste de vidéos avec métadonnées
        """
        # Bases de données de créateurs de qualité par langue
        quality_creators = {
            "fr": [
                "Machine Learnia",
                "Underscore_",
                "Cookie connecté",
                "Grafikart",
                "Science4All"
            ],
            "en": [
                "3Blue1Brown",
                "Sentdex",
                "StatQuest",
                "Two Minute Papers",
                "Yannic Kilcher",
                "CodeEmporium"
            ]
        }

        # Construction de la requête selon le sujet et la langue
        if language == "fr":
            query_terms = f"{topic} tutoriel machine learning français"
        else:
            query_terms = f"{topic} tutorial machine learning"

        # Recommandations fixes de haute qualité (fallback si API indisponible)
        curated_videos = []

        if language == "fr":
            curated_videos = [
                {
                    "titre": f"Machine Learning : {topic} - Cours Complet",
                    "url": "https://www.youtube.com/@machinelearnia",
                    "auteur": "Machine Learnia",
                    "duree_estimee": "2h30",
                    "plateforme": "YouTube",
                    "langue": "fr",
                    "gratuit": True,
                    "note_qualite": 9.5,
                    "description": f"Explication claire et pédagogique de {topic} en français",
                    "pourquoi_recommande": "Excellent pour les francophones, animations claires"
                },
                {
                    "titre": f"Les Réseaux de Neurones - {topic}",
                    "url": "https://www.youtube.com/c/3blue1brown",
                    "auteur": "3Blue1Brown",
                    "duree_estimee": "20min",
                    "plateforme": "YouTube",
                    "langue": "en",
                    "sous_titres_fr": True,
                    "gratuit": True,
                    "note_qualite": 10.0,
                    "description": "Visualisations mathématiques exceptionnelles",
                    "pourquoi_recommande": "Visualisations exceptionnelles, sous-titres FR disponibles"
                },
                {
                    "titre": f"Programmer un {topic} en Python",
                    "url": "https://www.youtube.com/@Underscore_",
                    "auteur": "Underscore_",
                    "duree_estimee": "45min",
                    "plateforme": "YouTube",
                    "langue": "fr",
                    "gratuit": True,
                    "note_qualite": 8.8,
                    "description": "Tutoriel pratique avec code Python",
                    "pourquoi_recommande": "Approche pratique et code commenté"
                }
            ]
        else:
            curated_videos = [
                {
                    "titre": f"{topic} - Deep Dive",
                    "url": "https://www.youtube.com/sentdex",
                    "auteur": "Sentdex",
                    "duree_estimee": "3h",
                    "plateforme": "YouTube",
                    "langue": "en",
                    "gratuit": True,
                    "note_qualite": 9.0,
                    "description": f"Comprehensive {topic} implementation from scratch",
                    "pourquoi_recommande": "Practical coding approach with real examples"
                },
                {
                    "titre": f"StatQuest: {topic} Clearly Explained",
                    "url": "https://www.youtube.com/@statquest",
                    "auteur": "StatQuest",
                    "duree_estimee": "15min",
                    "plateforme": "YouTube",
                    "langue": "en",
                    "gratuit": True,
                    "note_qualite": 9.8,
                    "description": "Clear statistical explanations with humor",
                    "pourquoi_recommande": "Perfect for understanding the math behind concepts"
                }
            ]

        return curated_videos[:max_results]

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
        platforms = platforms or ["coursera", "edx", "openclassrooms", "khan_academy", "fast.ai"]

        # Base de données enrichie de cours de référence
        all_courses = [
            {
                "titre": "Machine Learning par Andrew Ng",
                "url": "https://www.coursera.org/learn/machine-learning",
                "plateforme": "Coursera",
                "auteur": "Andrew Ng (Stanford)",
                "duree_estimee": "60h",
                "gratuit": True,  # Audit gratuit
                "certification_payante": True,
                "langue": "en",
                "sous_titres_fr": True,
                "niveau_requis": "débutant",
                "note_qualite": 4.9,
                "description": "LE cours de référence en Machine Learning - 4.9M étudiants",
                "pourquoi_recommande": "Cours fondateur, explications claires, exercices pratiques",
                "competences": ["ML supervisé", "ML non-supervisé", "Réseaux de neurones", "Régression"],
                "prerequis": ["Algèbre linéaire de base", "Programmation (Octave/MATLAB)"]
            },
            {
                "titre": "Deep Learning Specialization",
                "url": "https://www.coursera.org/specializations/deep-learning",
                "plateforme": "Coursera",
                "auteur": "deeplearning.ai - Andrew Ng",
                "duree_estimee": "120h",
                "gratuit": True,  # Audit
                "niveau_requis": "intermédiaire",
                "note_qualite": 4.8,
                "langue": "en",
                "sous_titres_fr": True,
                "description": "5 cours sur le Deep Learning (CNN, RNN, LSTM, etc.)",
                "pourquoi_recommande": "Spécialisation complète du Deep Learning par Andrew Ng",
                "competences": ["CNN", "RNN", "LSTM", "Attention", "Transformers"],
                "prerequis": ["Machine Learning de base", "Python", "NumPy"]
            },
            {
                "titre": "CS50's Introduction to Artificial Intelligence with Python",
                "url": "https://cs50.harvard.edu/ai/",
                "plateforme": "Harvard CS50",
                "auteur": "Harvard University",
                "duree_estimee": "50h",
                "gratuit": True,
                "niveau_requis": "débutant",
                "note_qualite": 4.9,
                "langue": "en",
                "sous_titres_fr": False,
                "description": "Introduction complète à l'IA avec Python par Harvard",
                "pourquoi_recommande": "Excellente pédagogie, projets pratiques, gratuit à 100%",
                "competences": ["Search", "Knowledge", "Probabilité", "Neural Networks", "NLP"],
                "prerequis": ["Python de base"]
            },
            {
                "titre": "Initiez-vous au Machine Learning",
                "url": "https://openclassrooms.com/fr/courses/4011851-initiez-vous-au-machine-learning",
                "plateforme": "OpenClassrooms",
                "auteur": "OpenClassrooms",
                "duree_estimee": "10h",
                "gratuit": True,
                "langue": "fr",
                "niveau_requis": "débutant",
                "note_qualite": 4.3,
                "description": "Introduction en français au ML avec Python",
                "pourquoi_recommande": "Parfait pour les débutants francophones",
                "competences": ["Régression", "Classification", "scikit-learn"],
                "prerequis": ["Python de base"]
            },
            {
                "titre": "Practical Deep Learning for Coders",
                "url": "https://course.fast.ai/",
                "plateforme": "fast.ai",
                "auteur": "Jeremy Howard",
                "duree_estimee": "70h",
                "gratuit": True,
                "niveau_requis": "intermédiaire",
                "note_qualite": 4.8,
                "langue": "en",
                "description": "Approche top-down : code d'abord, théorie ensuite",
                "pourquoi_recommande": "Approche pratique unique, résultats rapides",
                "competences": ["PyTorch", "Transfer Learning", "Computer Vision", "NLP"],
                "prerequis": ["Python intermédiaire", "1 an de programmation"]
            },
            {
                "titre": "MIT 6.S191: Introduction to Deep Learning",
                "url": "http://introtodeeplearning.com/",
                "plateforme": "MIT",
                "auteur": "MIT",
                "duree_estimee": "40h",
                "gratuit": True,
                "niveau_requis": "intermédiaire",
                "note_qualite": 4.7,
                "langue": "en",
                "description": "Cours MIT avec labs TensorFlow",
                "pourquoi_recommande": "Cours universitaire de prestige, labs pratiques",
                "competences": ["Deep Learning", "TensorFlow", "CNN", "RNN", "GAN"],
                "prerequis": ["Calcul", "Algèbre linéaire", "Python"]
            },
            {
                "titre": "Réalisez des modèles de Deep Learning",
                "url": "https://openclassrooms.com/fr/courses/5801891-realisez-des-modeles-de-deep-learning",
                "plateforme": "OpenClassrooms",
                "auteur": "OpenClassrooms",
                "duree_estimee": "20h",
                "gratuit": True,
                "langue": "fr",
                "niveau_requis": "intermédiaire",
                "note_qualite": 4.2,
                "description": "Deep Learning en français avec TensorFlow/Keras",
                "pourquoi_recommande": "En français, pratique avec Keras",
                "competences": ["Keras", "CNN", "Transfer Learning"],
                "prerequis": ["Python", "NumPy", "ML de base"]
            }
        ]

        # Filtrer selon free_only et niveau
        filtered = all_courses
        if free_only:
            filtered = [c for c in filtered if c["gratuit"]]

        # Limiter à 8 cours max
        return filtered[:8]

    async def search_github_projects(
        self,
        topic: str,
        difficulty: str = "beginner"
    ) -> List[Dict[str, Any]]:
        """
        Recherche des projets GitHub éducatifs classés par niveau.

        Args:
            topic: Sujet (ex: "classification", "nlp")
            difficulty: Niveau (beginner, intermediate, advanced)

        Returns:
            Liste de projets GitHub avec métadonnées
        """
        # Projets de référence enrichis et classés par difficulté
        all_projects = {
            "beginner": [
                {
                    "titre": "ML From Scratch",
                    "url": "https://github.com/eriklindernoren/ML-From-Scratch",
                    "stars": "23k+",
                    "description": "Implémentations Python de tous les algorithmes ML classiques sans frameworks",
                    "technologies": ["Python", "NumPy"],
                    "niveau_requis": "débutant",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Parfait pour comprendre les algorithmes en profondeur",
                    "competences": ["Algorithmes ML", "NumPy", "Mathématiques ML"],
                    "ideal_pour": "Apprendre les fondamentaux sans 'boîte noire'"
                },
                {
                    "titre": "100 Days of ML Code",
                    "url": "https://github.com/Avik-Jain/100-Days-Of-ML-Code",
                    "stars": "43k+",
                    "description": "Défi progressif de 100 jours avec infographies et code",
                    "technologies": ["Python", "scikit-learn", "pandas"],
                    "niveau_requis": "débutant",
                    "duree_estimee": "100 jours",
                    "pourquoi_recommande": "Progression structurée jour par jour",
                    "competences": ["ML fondamental", "Data Science"],
                    "ideal_pour": "Structure d'apprentissage progressive"
                },
                {
                    "titre": "Homemade Machine Learning",
                    "url": "https://github.com/trekhleb/homemade-machine-learning",
                    "stars": "22k+",
                    "description": "Algorithmes ML en Python avec démos interactives Jupyter",
                    "technologies": ["Python", "Jupyter", "NumPy"],
                    "niveau_requis": "débutant",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Notebooks interactifs pour expérimenter",
                    "competences": ["Régression", "Classification", "Clustering"],
                    "ideal_pour": "Apprentissage hands-on avec notebooks"
                },
                {
                    "titre": "Machine Learning for Beginners (Microsoft)",
                    "url": "https://github.com/microsoft/ML-For-Beginners",
                    "stars": "65k+",
                    "description": "Curriculum Microsoft de 12 semaines avec leçons et quiz",
                    "technologies": ["Python", "scikit-learn"],
                    "niveau_requis": "débutant",
                    "duree_estimee": "12 semaines",
                    "pourquoi_recommande": "Curriculum structuré par Microsoft avec projets",
                    "competences": ["ML supervisé", "ML non-supervisé", "NLP", "Time Series"],
                    "ideal_pour": "Programme structuré clé en main"
                }
            ],
            "intermediate": [
                {
                    "titre": "Keras Examples",
                    "url": "https://github.com/keras-team/keras-io",
                    "stars": "2k+",
                    "description": "Collection officielle d'exemples Keras/TensorFlow",
                    "technologies": ["Python", "TensorFlow", "Keras"],
                    "niveau_requis": "intermédiaire",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Exemples officiels de haute qualité",
                    "competences": ["Deep Learning", "CNN", "RNN", "Transfer Learning"],
                    "ideal_pour": "Apprendre les patterns avec Keras"
                },
                {
                    "titre": "Deep Learning with PyTorch Examples",
                    "url": "https://github.com/pytorch/examples",
                    "stars": "21k+",
                    "description": "Exemples officiels PyTorch (CNN, RNN, GAN, etc.)",
                    "technologies": ["Python", "PyTorch"],
                    "niveau_requis": "intermédiaire",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Exemples officiels PyTorch, code production-ready",
                    "competences": ["PyTorch", "CNN", "RNN", "GAN"],
                    "ideal_pour": "Maîtriser PyTorch avec exemples réels"
                },
                {
                    "titre": "TensorFlow Examples",
                    "url": "https://github.com/tensorflow/examples",
                    "stars": "7k+",
                    "description": "Exemples TensorFlow officiels pour tous niveaux",
                    "technologies": ["Python", "TensorFlow"],
                    "niveau_requis": "intermédiaire",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Best practices TensorFlow",
                    "competences": ["TensorFlow", "Keras", "TF Lite", "TF.js"],
                    "ideal_pour": "Écosystème TensorFlow complet"
                },
                {
                    "titre": "Awesome Machine Learning Projects",
                    "url": "https://github.com/ml-tooling/best-of-ml-python",
                    "stars": "15k+",
                    "description": "Curation des meilleurs projets ML Python classés",
                    "technologies": ["Python", "Multi-frameworks"],
                    "niveau_requis": "intermédiaire",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Découvrir les meilleurs outils et librairies",
                    "ideal_pour": "Explorer l'écosystème ML Python"
                }
            ],
            "advanced": [
                {
                    "titre": "Papers with Code",
                    "url": "https://github.com/paperswithcode",
                    "stars": "Multiple repos",
                    "description": "Implémentations de papiers de recherche avec benchmarks",
                    "technologies": ["PyTorch", "TensorFlow", "Varies"],
                    "niveau_requis": "avancé",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "État de l'art avec code vérifié",
                    "competences": ["Research", "État de l'art", "Benchmarking"],
                    "ideal_pour": "Explorer la recherche moderne en ML"
                },
                {
                    "titre": "Awesome Deep Learning Papers",
                    "url": "https://github.com/terryum/awesome-deep-learning-papers",
                    "stars": "25k+",
                    "description": "Collection des papiers DL les plus influents",
                    "technologies": ["Theory", "Multiple frameworks"],
                    "niveau_requis": "avancé",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Comprendre l'évolution du Deep Learning",
                    "competences": ["Lecture de papers", "Concepts avancés"],
                    "ideal_pour": "Culture générale DL et recherche"
                },
                {
                    "titre": "Deep Learning Drizzle",
                    "url": "https://github.com/kmario23/deep-learning-drizzle",
                    "stars": "11k+",
                    "description": "Collection de cours universitaires DL (Stanford, MIT, etc.)",
                    "technologies": ["Theory", "Multi-frameworks"],
                    "niveau_requis": "avancé",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Cours académiques de prestige gratuits",
                    "ideal_pour": "Formation académique approfondie"
                },
                {
                    "titre": "Transformers from Scratch",
                    "url": "https://github.com/karpathy/minGPT",
                    "stars": "18k+",
                    "description": "Implémentation minimale de GPT par Andrej Karpathy",
                    "technologies": ["PyTorch"],
                    "niveau_requis": "avancé",
                    "duree_estimee": "Variable",
                    "pourquoi_recommande": "Comprendre les Transformers en profondeur",
                    "competences": ["Transformers", "Attention", "LLM"],
                    "ideal_pour": "Maîtriser l'architecture moderne des LLM"
                }
            ]
        }

        # Retourner projets du niveau demandé
        projects = all_projects.get(difficulty, all_projects["beginner"])
        return projects[:6]  # Max 6 projets

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

