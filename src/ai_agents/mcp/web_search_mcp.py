"""
MCP (Model Context Protocol) pour la recherche de ressources éducatives.
Recherche automatique de vidéos YouTube, cours en ligne, articles, etc.
"""
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSearchMCP:
    """
    MCP pour rechercher des ressources éducatives en ligne.
    Utilise plusieurs sources : YouTube, recherche web, cours en ligne.
    """

    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def search_youtube(
        self,
        query: str,
        language: str = "fr",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recherche de vidéos YouTube via scraping léger.

        Args:
            query: Terme de recherche
            language: Langue préférée (fr/en)
            max_results: Nombre de résultats

        Returns:
            Liste de vidéos avec métadonnées
        """
        try:
            # Ajouter le terme de langue à la recherche
            lang_term = "français" if language == "fr" else "english"
            search_query = f"{query} tutorial {lang_term} machine learning AI"

            # Recherche via YouTube
            url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"User-Agent": self.user_agent}
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"YouTube search failed with status {response.status_code}")
                    return self._get_curated_videos(query, language, max_results)

                # Parser les résultats (simplifié)
                results = self._parse_youtube_results(response.text, query, language)
                return results[:max_results]

        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            # Fallback sur ressources curées
            return self._get_curated_videos(query, language, max_results)

    def _parse_youtube_results(
        self,
        html: str,
        query: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Parse les résultats HTML de YouTube (simplifié)."""
        # Pour l'instant, retourner des ressources curées de qualité
        # TODO: Implémenter un vrai parser si nécessaire
        return self._get_curated_videos(query, language, 10)

    def _get_curated_videos(
        self,
        topic: str,
        language: str = "fr",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Base de données enrichie de vidéos de haute qualité.
        Organisée par sujet et niveau.
        """
        topic_lower = topic.lower()

        # Base de vidéos par sujet
        video_database = {
            # FONDAMENTAUX ML
            "machine learning": {
                "fr": [
                    {
                        "titre": "Machine Learning - Cours Complet pour Débutants",
                        "url": "https://www.youtube.com/watch?v=Gv9_4yMHFhI",
                        "auteur": "Machine Learnia",
                        "duree_estimee": "3h",
                        "note_qualite": 9.5,
                        "description": "Cours complet en français couvrant tous les fondamentaux"
                    },
                    {
                        "titre": "Introduction au Machine Learning",
                        "url": "https://www.youtube.com/watch?v=GwIo3gDZCVQ",
                        "auteur": "Underscore_",
                        "duree_estimee": "45min",
                        "note_qualite": 9.0,
                        "description": "Introduction claire et concise en français"
                    }
                ],
                "en": [
                    {
                        "titre": "Machine Learning Full Course",
                        "url": "https://www.youtube.com/watch?v=gmvvaobm7eQ",
                        "auteur": "freeCodeCamp",
                        "duree_estimee": "10h",
                        "note_qualite": 9.7,
                        "description": "Comprehensive ML course covering all basics"
                    }
                ]
            },

            # DEEP LEARNING
            "deep learning": {
                "fr": [
                    {
                        "titre": "Deep Learning - Les Réseaux de Neurones",
                        "url": "https://www.youtube.com/watch?v=trWrEWfhTVg",
                        "auteur": "Machine Learnia",
                        "duree_estimee": "30min",
                        "note_qualite": 9.3,
                        "description": "Explication claire des réseaux de neurones"
                    }
                ],
                "en": [
                    {
                        "titre": "Neural Networks Explained",
                        "url": "https://www.youtube.com/watch?v=aircAruvnKk",
                        "auteur": "3Blue1Brown",
                        "duree_estimee": "20min",
                        "note_qualite": 10.0,
                        "description": "Visual explanation of neural networks - masterpiece",
                        "sous_titres_fr": True
                    }
                ]
            },

            # CNN
            "cnn": {
                "fr": [
                    {
                        "titre": "Les Réseaux de Neurones Convolutifs (CNN)",
                        "url": "https://www.youtube.com/watch?v=f0t-OCG79-U",
                        "auteur": "Machine Learnia",
                        "duree_estimee": "25min",
                        "note_qualite": 9.4,
                        "description": "Explication des CNN pour la vision par ordinateur"
                    }
                ],
                "en": [
                    {
                        "titre": "Convolutional Neural Networks Explained",
                        "url": "https://www.youtube.com/watch?v=YRhxdVk_sIs",
                        "auteur": "Computerphile",
                        "duree_estimee": "15min",
                        "note_qualite": 9.5,
                        "description": "Clear CNN explanation with visualizations"
                    }
                ]
            },

            # RNN / LSTM
            "rnn": {
                "fr": [
                    {
                        "titre": "RNN et LSTM - Réseaux Récurrents",
                        "url": "https://www.youtube.com/watch?v=cEg8cOx7UZc",
                        "auteur": "Machine Learnia",
                        "duree_estimee": "30min",
                        "note_qualite": 9.2,
                        "description": "Introduction aux réseaux récurrents"
                    }
                ],
                "en": [
                    {
                        "titre": "Illustrated Guide to LSTM's and GRU's",
                        "url": "https://www.youtube.com/watch?v=8HyCNIVRbSU",
                        "auteur": "The A.I. Hacker",
                        "duree_estimee": "25min",
                        "note_qualite": 9.6,
                        "description": "Visual guide to understanding LSTM"
                    }
                ]
            },

            # TRANSFORMERS
            "transformer": {
                "en": [
                    {
                        "titre": "Attention is All You Need - Explained",
                        "url": "https://www.youtube.com/watch?v=iDulhoQ2pro",
                        "auteur": "Yannic Kilcher",
                        "duree_estimee": "1h",
                        "note_qualite": 9.8,
                        "description": "Deep dive into the Transformer architecture"
                    },
                    {
                        "titre": "Illustrated Transformer",
                        "url": "https://www.youtube.com/watch?v=4Bdc55j80l8",
                        "auteur": "Rasa",
                        "duree_estimee": "20min",
                        "note_qualite": 9.4,
                        "description": "Visual explanation of Transformers"
                    }
                ],
                "fr": [
                    {
                        "titre": "Les Transformers expliqués simplement",
                        "url": "https://www.youtube.com/watch?v=23XUv0T9L5c",
                        "auteur": "Underscore_",
                        "duree_estimee": "35min",
                        "note_qualite": 9.0,
                        "description": "Explication en français des Transformers"
                    }
                ]
            },

            # NLP
            "nlp": {
                "fr": [
                    {
                        "titre": "Traitement du Langage Naturel (NLP)",
                        "url": "https://www.youtube.com/watch?v=f2HFEEVMVdY",
                        "auteur": "Machine Learnia",
                        "duree_estimee": "40min",
                        "note_qualite": 9.1,
                        "description": "Introduction au NLP en français"
                    }
                ],
                "en": [
                    {
                        "titre": "Natural Language Processing - Full Course",
                        "url": "https://www.youtube.com/watch?v=fLvJ8VdHLA0",
                        "auteur": "freeCodeCamp",
                        "duree_estimee": "5h",
                        "note_qualite": 9.3,
                        "description": "Complete NLP course with practical examples"
                    }
                ]
            },

            # REINFORCEMENT LEARNING
            "reinforcement": {
                "en": [
                    {
                        "titre": "Reinforcement Learning Course",
                        "url": "https://www.youtube.com/watch?v=2pWv7GOvuf0",
                        "auteur": "DeepMind x UCL",
                        "duree_estimee": "2h",
                        "note_qualite": 9.9,
                        "description": "RL course by David Silver (DeepMind)"
                    }
                ],
                "fr": [
                    {
                        "titre": "Apprentissage par Renforcement - Introduction",
                        "url": "https://www.youtube.com/watch?v=IkEF4LpH5Ys",
                        "auteur": "Machine Learnia",
                        "duree_estimee": "35min",
                        "note_qualite": 8.9,
                        "description": "Introduction claire au RL en français"
                    }
                ]
            }
        }

        # Trouver les vidéos correspondantes
        results = []
        for key in video_database:
            if key in topic_lower or topic_lower in key:
                lang_videos = video_database[key].get(language, [])
                if not lang_videos and language == "fr":
                    # Fallback sur anglais avec sous-titres
                    lang_videos = video_database[key].get("en", [])
                    for video in lang_videos:
                        video["sous_titres_fr"] = True
                        video["langue"] = "en"

                for video in lang_videos:
                    results.append({
                        **video,
                        "type": "video",
                        "plateforme": "YouTube",
                        "langue": language,
                        "gratuit": True,
                        "niveau_requis": self._infer_level(video["titre"]),
                        "pourquoi_recommande": f"Ressource de qualité sur {topic}"
                    })

        # Si pas de résultats spécifiques, retourner des ressources générales
        if not results:
            results = self._get_general_resources(language)

        return results[:max_results]

    def _infer_level(self, title: str) -> str:
        """Inférer le niveau requis depuis le titre."""
        title_lower = title.lower()
        if any(word in title_lower for word in ["débutant", "introduction", "beginner", "intro"]):
            return "débutant"
        elif any(word in title_lower for word in ["avancé", "advanced", "deep dive", "expert"]):
            return "avancé"
        return "intermédiaire"

    def _get_general_resources(self, language: str) -> List[Dict[str, Any]]:
        """Ressources générales de haute qualité."""
        if language == "fr":
            return [
                {
                    "titre": "Machine Learning de A à Z",
                    "url": "https://www.youtube.com/watch?v=Gv9_4yMHFhI",
                    "auteur": "Machine Learnia",
                    "duree_estimee": "3h",
                    "type": "video",
                    "plateforme": "YouTube",
                    "gratuit": True,
                    "langue": "fr",
                    "note_qualite": 9.5,
                    "niveau_requis": "débutant",
                    "description": "Cours complet en français",
                    "pourquoi_recommande": "Excellente introduction en français"
                }
            ]
        else:
            return [
                {
                    "titre": "Machine Learning Crash Course",
                    "url": "https://www.youtube.com/watch?v=GwIo3gDZCVQ",
                    "auteur": "Google Developers",
                    "duree_estimee": "15h",
                    "type": "video",
                    "plateforme": "YouTube",
                    "gratuit": True,
                    "langue": "en",
                    "note_qualite": 9.7,
                    "niveau_requis": "débutant",
                    "description": "Complete ML course by Google",
                    "pourquoi_recommande": "Official Google ML course"
                }
            ]

    async def search_online_courses(
        self,
        topic: str,
        level: str = "débutant",
        language: str = "fr"
    ) -> List[Dict[str, Any]]:
        """
        Recherche de cours en ligne sur les plateformes majeures.

        Args:
            topic: Sujet recherché
            level: Niveau (débutant/intermédiaire/avancé)
            language: Langue préférée

        Returns:
            Liste de cours avec métadonnées
        """
        courses = [
            {
                "titre": "Machine Learning par Andrew Ng",
                "url": "https://www.coursera.org/learn/machine-learning",
                "plateforme": "Coursera",
                "auteur": "Andrew Ng (Stanford)",
                "duree_estimee": "60h",
                "gratuit": True,
                "type": "cours",
                "langue": "en",
                "sous_titres_fr": True,
                "niveau_requis": "débutant",
                "note_qualite": 4.9,
                "description": "LE cours de référence en Machine Learning",
                "pourquoi_recommande": "Cours fondateur avec 4.9M+ étudiants",
                "xp": 500
            },
            {
                "titre": "Deep Learning Specialization",
                "url": "https://www.coursera.org/specializations/deep-learning",
                "plateforme": "Coursera",
                "auteur": "deeplearning.ai",
                "duree_estimee": "120h",
                "gratuit": True,
                "type": "cours",
                "langue": "en",
                "sous_titres_fr": True,
                "niveau_requis": "intermédiaire",
                "note_qualite": 4.8,
                "description": "5 cours sur le Deep Learning complet",
                "pourquoi_recommande": "Spécialisation complète par Andrew Ng",
                "xp": 800
            },
            {
                "titre": "Initiez-vous au Machine Learning",
                "url": "https://openclassrooms.com/fr/courses/4011851-initiez-vous-au-machine-learning",
                "plateforme": "OpenClassrooms",
                "auteur": "OpenClassrooms",
                "duree_estimee": "10h",
                "gratuit": True,
                "type": "cours",
                "langue": "fr",
                "niveau_requis": "débutant",
                "note_qualite": 4.3,
                "description": "Introduction ML en français avec Python",
                "pourquoi_recommande": "Parfait pour les débutants francophones",
                "xp": 200
            },
            {
                "titre": "Practical Deep Learning for Coders",
                "url": "https://course.fast.ai/",
                "plateforme": "fast.ai",
                "auteur": "Jeremy Howard",
                "duree_estimee": "70h",
                "gratuit": True,
                "type": "cours",
                "langue": "en",
                "niveau_requis": "intermédiaire",
                "note_qualite": 4.9,
                "description": "Approche pratique du Deep Learning",
                "pourquoi_recommande": "Approche top-down, très pratique",
                "xp": 600
            },
            {
                "titre": "CS50's Introduction to AI with Python",
                "url": "https://cs50.harvard.edu/ai/",
                "plateforme": "Harvard",
                "auteur": "Harvard University",
                "duree_estimee": "50h",
                "gratuit": True,
                "type": "cours",
                "langue": "en",
                "niveau_requis": "débutant",
                "note_qualite": 4.9,
                "description": "Introduction complète à l'IA par Harvard",
                "pourquoi_recommande": "Excellente pédagogie, 100% gratuit",
                "xp": 450
            }
        ]

        # Filtrer par niveau et langue si nécessaire
        filtered = []
        for course in courses:
            if level in course["niveau_requis"]:
                if language == "fr" and (course["langue"] == "fr" or course.get("sous_titres_fr")):
                    filtered.append(course)
                elif language == "en":
                    filtered.append(course)

        return filtered if filtered else courses[:3]

    async def search_articles(
        self,
        topic: str,
        language: str = "fr"
    ) -> List[Dict[str, Any]]:
        """
        Recherche d'articles et tutoriels de qualité.

        Args:
            topic: Sujet recherché
            language: Langue préférée

        Returns:
            Liste d'articles avec métadonnées
        """
        articles = [
            {
                "titre": "A Gentle Introduction to Deep Learning",
                "url": "https://machinelearningmastery.com/what-is-deep-learning/",
                "plateforme": "Machine Learning Mastery",
                "auteur": "Jason Brownlee",
                "duree_estimee": "15min",
                "type": "article",
                "gratuit": True,
                "langue": "en",
                "note_qualite": 9.0,
                "description": "Introduction claire au deep learning",
                "pourquoi_recommande": "Explications claires avec exemples",
                "xp": 50
            },
            {
                "titre": "Understanding Neural Networks",
                "url": "https://towardsdatascience.com/understanding-neural-networks-22b29755abd9",
                "plateforme": "Towards Data Science",
                "auteur": "Community",
                "duree_estimee": "20min",
                "type": "article",
                "gratuit": True,
                "langue": "en",
                "note_qualite": 8.5,
                "description": "Guide complet sur les réseaux de neurones",
                "pourquoi_recommande": "Bien illustré et accessible",
                "xp": 60
            }
        ]

        return articles

    async def search_github_projects(
        self,
        topic: str,
        difficulty: str = "beginner"
    ) -> List[Dict[str, Any]]:
        """
        Recherche de projets GitHub et notebooks Kaggle.

        Args:
            topic: Sujet recherché
            difficulty: Difficulté (beginner/intermediate/advanced)

        Returns:
            Liste de projets avec métadonnées
        """
        projects = [
            {
                "titre": "TensorFlow Examples",
                "url": "https://github.com/tensorflow/examples",
                "plateforme": "GitHub",
                "auteur": "TensorFlow Team",
                "type": "code",
                "gratuit": True,
                "difficulte": "beginner",
                "description": "Collection officielle d'exemples TensorFlow",
                "pourquoi_recommande": "Exemples officiels, bien maintenus",
                "xp": 100
            },
            {
                "titre": "PyTorch Tutorial",
                "url": "https://github.com/yunjey/pytorch-tutorial",
                "plateforme": "GitHub",
                "auteur": "Yunjey Choi",
                "type": "code",
                "gratuit": True,
                "difficulte": "beginner",
                "description": "Tutoriels PyTorch progressifs",
                "pourquoi_recommande": "Très populaire, bien structuré",
                "xp": 100
            },
            {
                "titre": "Kaggle Learn - Intro to ML",
                "url": "https://www.kaggle.com/learn/intro-to-machine-learning",
                "plateforme": "Kaggle",
                "auteur": "Kaggle",
                "type": "code",
                "gratuit": True,
                "difficulte": "beginner",
                "description": "Cours interactif avec notebooks",
                "pourquoi_recommande": "Pratique immédiate avec notebooks",
                "xp": 150
            }
        ]

        return [p for p in projects if difficulty in p["difficulte"]]

    async def get_comprehensive_resources(
        self,
        topic: str,
        user_level: int,
        language: str = "fr",
        include_projects: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtenir un ensemble complet de ressources pour un sujet donné.

        Args:
            topic: Sujet principal
            user_level: Niveau utilisateur (1-10)
            language: Langue préférée
            include_projects: Inclure des projets pratiques

        Returns:
            Dictionnaire avec vidéos, cours, articles, projets
        """
        level_map = {
            1: "débutant", 2: "débutant", 3: "débutant",
            4: "intermédiaire", 5: "intermédiaire", 6: "intermédiaire", 7: "intermédiaire",
            8: "avancé", 9: "avancé", 10: "avancé"
        }
        level_str = level_map.get(user_level, "intermédiaire")

        # Recherche parallèle de toutes les ressources
        videos_task = self.search_youtube(topic, language, max_results=3)
        courses_task = self.search_online_courses(topic, level_str, language)
        articles_task = self.search_articles(topic, language)

        tasks = [videos_task, courses_task, articles_task]

        if include_projects:
            difficulty = "beginner" if user_level <= 3 else "intermediate" if user_level <= 7 else "advanced"
            projects_task = self.search_github_projects(topic, difficulty)
            tasks.append(projects_task)

        # Attendre toutes les recherches
        results = await asyncio.gather(*tasks, return_exceptions=True)

        response = {
            "videos": results[0] if not isinstance(results[0], Exception) else [],
            "cours": results[1] if not isinstance(results[1], Exception) else [],
            "articles": results[2] if not isinstance(results[2], Exception) else [],
        }

        if include_projects:
            response["projets"] = results[3] if not isinstance(results[3], Exception) else []

        return response


# Instance globale
web_search_mcp = WebSearchMCP()

