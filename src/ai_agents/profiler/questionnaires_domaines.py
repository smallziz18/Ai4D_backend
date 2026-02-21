"""
Générateur de questionnaires adaptés par domaine d'études.
Chaque domaine reçoit des questions spécifiques et contextualisées.
"""

from typing import List, Dict, Any
from enum import Enum


class DomainQuestionnaireGenerator:
    """Génère des questionnaires adaptés au domaine de l'utilisateur"""

    # Questions pour Informatique/Data Science/IA
    INFORMATIQUE_QUESTIONS = [
        {
            "id": "q1_info",
            "question": "Quel est votre niveau en programmation ?",
            "type": "multiple_choice",
            "options": [
                "A. Je débute avec la programmation",
                "B. Je maîtrise les bases (variables, boucles, conditions)",
                "C. Je suis à l'aise avec OOP et les structures de données",
                "D. Je peux concevoir et optimiser des architectures complexes"
            ],
            "domain": "Informatique"
        },
        {
            "id": "q2_info",
            "question": "Avez-vous une expérience avec les frameworks IA/ML ?",
            "type": "multiple_choice",
            "options": [
                "A. Aucune expérience",
                "B. J'ai suivi des tutoriels (TensorFlow, PyTorch, scikit-learn)",
                "C. J'ai réalisé des projets personnels avec ces outils",
                "D. J'ai des projets en production avec ces frameworks"
            ],
            "domain": "Informatique"
        },
        {
            "id": "q3_info",
            "question": "Quels sont vos objectifs principaux avec l'IA ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Informatique"
        }
    ]

    # Questions pour Droit
    DROIT_QUESTIONS = [
        {
            "id": "q1_droit",
            "question": "Quel domaine du droit vous intéresse le plus ?",
            "type": "multiple_choice",
            "options": [
                "A. Droit civil et contrats",
                "B. Droit pénal et criminel",
                "C. Droit commercial et propriété intellectuelle",
                "D. Droit de l'IA et régulation technologique"
            ],
            "domain": "Droit"
        },
        {
            "id": "q2_droit",
            "question": "Avez-vous entendu parler des enjeux légaux de l'IA ?",
            "type": "multiple_choice",
            "options": [
                "A. Non, c'est nouveau pour moi",
                "B. Oui, de façon superficielle (RGPD, lois sur l'IA)",
                "C. Oui, j'ai étudié les régulations actuelles",
                "D. Oui, je travaille déjà dans ce domaine"
            ],
            "domain": "Droit"
        },
        {
            "id": "q3_droit",
            "question": "Comment pensez-vous utiliser l'IA dans votre pratique juridique ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Droit"
        }
    ]

    # Questions pour Marketing
    MARKETING_QUESTIONS = [
        {
            "id": "q1_marketing",
            "question": "Quel type de marketing vous intéresse le plus ?",
            "type": "multiple_choice",
            "options": [
                "A. Marketing digital et réseaux sociaux",
                "B. Marketing d'audience et segmentation",
                "C. Marketing automation et personnalisation",
                "D. Data-driven marketing et analytics"
            ],
            "domain": "Marketing"
        },
        {
            "id": "q2_marketing",
            "question": "Avez-vous utilisé des outils d'IA pour vos campagnes marketing ?",
            "type": "multiple_choice",
            "options": [
                "A. Non, jamais",
                "B. Oui, des outils basiques (recommandations, tri de données)",
                "C. Oui, j'ai utilisé du machine learning pour la prédiction",
                "D. Oui, j'ai implémenté des systèmes de recommendation avancés"
            ],
            "domain": "Marketing"
        },
        {
            "id": "q3_marketing",
            "question": "Quel est votre principal défi marketing actuellement ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Marketing"
        }
    ]

    # Questions pour Médecine
    MEDECINE_QUESTIONS = [
        {
            "id": "q1_medecine",
            "question": "Quel domaine médical vous intéresse le plus ?",
            "type": "multiple_choice",
            "options": [
                "A. Diagnostic et imagerie médicale",
                "B. Traitement et pharmacologie",
                "C. Santé publique et épidémiologie",
                "D. Recherche biomédicale"
            ],
            "domain": "Médecine"
        },
        {
            "id": "q2_medecine",
            "question": "Êtes-vous conscient de l'utilisation de l'IA en médecine ?",
            "type": "multiple_choice",
            "options": [
                "A. Peu ou pas du tout",
                "B. Oui, j'ai entendu parler de systèmes d'IA médicaux",
                "C. Oui, je comprends le potentiel de l'IA en diagnostic",
                "D. Oui, j'ai expérience avec des outils IA médicaux"
            ],
            "domain": "Médecine"
        },
        {
            "id": "q3_medecine",
            "question": "Comment envisagez-vous d'appliquer l'IA dans votre pratique médicale ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Médecine"
        }
    ]

    # Questions pour Chimie
    CHIMIE_QUESTIONS = [
        {
            "id": "q1_chimie",
            "question": "Quel domaine de la chimie vous intéresse ?",
            "type": "multiple_choice",
            "options": [
                "A. Chimie organique et synthèse",
                "B. Chimie inorganique et matériaux",
                "C. Chimie analytique et instrumentation",
                "D. Chimie computationnelle et modélisation"
            ],
            "domain": "Chimie"
        },
        {
            "id": "q2_chimie",
            "question": "Avez-vous utilisé l'IA pour modéliser ou prédire des composés ?",
            "type": "multiple_choice",
            "options": [
                "A. Non, je n'ai pas d'expérience",
                "B. Oui, j'ai utilisé des simulations de base",
                "C. Oui, j'utilise le machine learning pour prédire des propriétés",
                "D. Oui, j'utilise des modèles deep learning avancés"
            ],
            "domain": "Chimie"
        },
        {
            "id": "q3_chimie",
            "question": "Quel est votre objectif en apprenant l'IA appliquée à la chimie ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Chimie"
        }
    ]

    # Questions pour Physique
    PHYSIQUE_QUESTIONS = [
        {
            "id": "q1_physique",
            "question": "Quel domaine de la physique vous intéresse le plus ?",
            "type": "multiple_choice",
            "options": [
                "A. Mécanique classique et quantique",
                "B. Thermodynamique et physique statistique",
                "C. Électromagnétisme et optique",
                "D. Astrophysique et physique des particules"
            ],
            "domain": "Physique"
        },
        {
            "id": "q2_physique",
            "question": "Avez-vous expérience avec la simulation numérique ?",
            "type": "multiple_choice",
            "options": [
                "A. Non, je suis nouveau en simulation",
                "B. Oui, j'ai fait des simulations basiques",
                "C. Oui, j'utilise Python ou MATLAB pour la modélisation",
                "D. Oui, je maîtrise les méthodes numériques avancées"
            ],
            "domain": "Physique"
        },
        {
            "id": "q3_physique",
            "question": "Comment pensez-vous appliquer l'IA à vos problèmes physiques ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Physique"
        }
    ]

    # Questions pour Économie
    ECONOMIE_QUESTIONS = [
        {
            "id": "q1_economie",
            "question": "Quel domaine économique vous intéresse le plus ?",
            "type": "multiple_choice",
            "options": [
                "A. Macroéconomie et politique monétaire",
                "B. Microéconomie et théorie des jeux",
                "C. Économétrie et analyse de données",
                "D. Finance et investissement"
            ],
            "domain": "Économie"
        },
        {
            "id": "q2_economie",
            "question": "Avez-vous expérience avec l'analyse de données économiques ?",
            "type": "multiple_choice",
            "options": [
                "A. Non, c'est nouveau pour moi",
                "B. Oui, j'utilise Excel et des statistiques basiques",
                "C. Oui, j'utilise Python/R pour l'analyse",
                "D. Oui, je maîtrise les modèles économétriques avancés"
            ],
            "domain": "Économie"
        },
        {
            "id": "q3_economie",
            "question": "Quel type de prédiction économique vous intéresse le plus ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Économie"
        }
    ]

    # Questions générales (par défaut)
    GENERAL_QUESTIONS = [
        {
            "id": "q1_general",
            "question": "Quel est votre niveau de connaissances en IA actuellement ?",
            "type": "multiple_choice",
            "options": [
                "A. Je débute totalement",
                "B. J'ai des connaissances basiques",
                "C. J'ai une bonne compréhension conceptuelle",
                "D. Je maîtrise bien l'IA et ses applications"
            ],
            "domain": "Général"
        },
        {
            "id": "q2_general",
            "question": "Quel est votre principal objectif d'apprentissage ?",
            "type": "multiple_choice",
            "options": [
                "A. Comprendre les concepts fondamentaux",
                "B. Acquérir des compétences pratiques",
                "C. Avancer dans ma carrière",
                "D. Devenir expert dans mon domaine"
            ],
            "domain": "Général"
        },
        {
            "id": "q3_general",
            "question": "Pourquoi voulez-vous apprendre l'IA ?",
            "type": "open_ended",
            "max_words": 100,
            "domain": "Général"
        }
    ]

    DOMAIN_MAPPING = {
        "Informatique": INFORMATIQUE_QUESTIONS,
        "Data Science": INFORMATIQUE_QUESTIONS,  # Même questionnaire que Informatique
        "Droit": DROIT_QUESTIONS,
        "Marketing": MARKETING_QUESTIONS,
        "Chimie": CHIMIE_QUESTIONS,
        "Physique": PHYSIQUE_QUESTIONS,
        "Médecine": MEDECINE_QUESTIONS,
        "Biologie": MEDECINE_QUESTIONS,  # Similaire à Médecine
        "Économie": ECONOMIE_QUESTIONS,
        "Management": MARKETING_QUESTIONS,  # Similaire à Marketing
        "Général": GENERAL_QUESTIONS,
    }

    @staticmethod
    def get_questions_for_domain(domain: str) -> List[Dict[str, Any]]:
        """Récupère les questions adaptées pour un domaine donné"""
        questions = DomainQuestionnaireGenerator.DOMAIN_MAPPING.get(
            domain,
            DomainQuestionnaireGenerator.GENERAL_QUESTIONS
        )
        return questions

    @staticmethod
    def get_all_domains() -> List[str]:
        """Retourne la liste de tous les domaines supportés"""
        return list(DomainQuestionnaireGenerator.DOMAIN_MAPPING.keys())

