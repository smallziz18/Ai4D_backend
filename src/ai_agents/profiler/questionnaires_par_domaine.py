"""
Questionnaires pré-définis adaptés à chaque domaine professionnel.
Chaque domaine a ses propres questions et cas d'usage.
"""
import random

# Pool de questions variées par domaine - Pour éviter la répétition
QUESTION_POOLS = {
    "Droit & Justice": {
        "debutant": [
            {
                "question": "L'IA peut-elle aider dans l'analyse de documents juridiques ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Oui, pour extraire automatiquement les clauses importantes",
                    "B. Non, l'IA ne comprend pas le langage juridique",
                    "C. Seulement pour les contrats simples",
                    "D. Uniquement en anglais"
                ],
                "correction": "A - Les systèmes IA peuvent analyser et extraire des informations juridiques pertinentes",
            },
            {
                "question": "Qu'est-ce que la prédiction de décisions judiciaires par IA ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Un système qui prédit le résultat probable d'une décision de justice",
                    "B. Un système qui décide à la place du juge",
                    "C. Un système qui génère des documents juridiques",
                    "D. Cela n'existe pas"
                ],
                "correction": "A - Les systèmes prédictifs analysent les données passées pour estimer les résultats possibles",
            },
            {
                "question": "L'IA peut-elle automatiser la rédaction de contrats simples ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Oui, en utilisant des modèles de textes pré-établis",
                    "B. Non, c'est toujours manuel",
                    "C. Seulement avec supervision humaine",
                    "D. Impossible techniquement"
                ],
                "correction": "A - L'IA peut générer des contrats de base qui sont ensuite validés par un humain",
            },
        ],
        "intermediaire": [
            {
                "question": "Quel risque éthique majeur pose l'IA en matière juridique ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Les biais algorithmiques qui pourraient discriminer certains groupes",
                    "B. La consommation d'électricité excessive",
                    "C. L'impossibilité de traiter les contrats internationaux",
                    "D. L'IA ne pose aucun risque en droit"
                ],
                "correction": "A - Les biais dans les données d'entraînement peuvent perpétuer des discriminations",
            },
            {
                "question": "Comment l'IA transforme-t-elle la pratique du droit ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Elle remplace complètement les avocats",
                    "B. Elle automatise la recherche juridique et l'analyse de documents",
                    "C. Elle n'a aucun impact sur le droit",
                    "D. Elle remplace uniquement les juges"
                ],
                "correction": "B - L'IA assiste les professionnels du droit en automatisant les tâches répétitives",
            },
            {
                "question": "Comment assurer la responsabilité légale quand l'IA commet une erreur juridique ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. L'IA n'a pas de responsabilité légale",
                    "B. Le développeur est toujours responsable",
                    "C. C'est une zone grise à définir légalement",
                    "D. L'utilisateur final est seul responsable"
                ],
                "correction": "C - La responsabilité légale de l'IA est encore un sujet de débat juridique",
            },
        ],
        "avance": [
            {
                "question": "Expliquez comment vous envisagez d'utiliser l'IA dans votre pratique juridique",
                "type": "QuestionOuverte",
                "correction": "Réponse attendue : cas d'usage concret comme recherche juridique, rédaction de contrats, analyse de documents",
            },
        ]
    },
    "Marketing & Communication": {
        "debutant": [
            {
                "question": "Comment l'IA peut-elle améliorer la segmentation des clients ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. En identifiant automatiquement les patterns et groupes de clients similaires",
                    "B. En supprimant les mauvais clients",
                    "C. En créant des groupes aléatoires",
                    "D. L'IA ne peut pas aider au marketing"
                ],
                "correction": "A - L'IA utilise le clustering pour identifier des segments clients automatiquement",
            },
            {
                "question": "Qu'est-ce qu'un système de recommandation personnalisée ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Un système qui propose les mêmes produits à tous",
                    "B. Un système qui prédit ce que chaque client veut acheter",
                    "C. Un système aléatoire",
                    "D. L'IA ne peut pas recommander"
                ],
                "correction": "B - Un système IA prédit ce que chaque client veut acheter en fonction de son historique",
            },
            {
                "question": "Comment l'IA peut-elle aider à la génération de contenu marketing ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Elle ne peut pas générer du contenu",
                    "B. Elle peut générer du texte et des descriptions rapidement",
                    "C. Elle remplace complètement les rédacteurs",
                    "D. Elle ne fonctionne qu'en anglais"
                ],
                "correction": "B - L'IA génère du contenu rapidement mais nécessite une vérification humaine",
            },
        ],
        "intermediaire": [
            {
                "question": "Quel est le risque principal de l'IA dans les campagnes marketing ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. La manipulation des consommateurs via hyper-personnalisation",
                    "B. L'absence de publicité",
                    "C. Les clients n'aiment pas les emails",
                    "D. L'IA n'a aucun impact"
                ],
                "correction": "A - La hyper-personnalisation peut manipuler les consommateurs de manière non éthique",
            },
            {
                "question": "Comment préserver la vie privée tout en utilisant l'IA pour le marketing ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Collecter le maximum de données possible",
                    "B. Anonymiser les données et respecter le RGPD",
                    "C. Ignorer les demandes de consentement",
                    "D. Rien n'est possible"
                ],
                "correction": "B - L'anonymisation et le respect du RGPD sont essentiels",
            },
        ],
        "avance": [
            {
                "question": "Décrivez une stratégie marketing IA complète pour votre secteur",
                "type": "QuestionOuverte",
                "correction": "Réponse attendue : combination de segmentation, personnalisation et conformité éthique",
            },
        ]
    },
    "Informatique & Développement": {
        "debutant": [
            {
                "question": "Qu'est-ce qu'un réseau de neurones convolutif (CNN) ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Un réseau spécialisé pour traiter les images",
                    "B. Un réseau pour le traitement du texte",
                    "C. Un réseau qui simule des circuits électriques",
                    "D. Un réseau de communication informatique"
                ],
                "correction": "A - Les CNN sont optimisés pour la vision par ordinateur",
            },
            {
                "question": "Qu'est-ce que le machine learning ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Une technique où les programmes apprennent des données",
                    "B. Une machine qui apprend à penser",
                    "C. Un type d'ordinateur rapide",
                    "D. Une théorie sans application pratique"
                ],
                "correction": "A - Le machine learning permet aux programmes d'apprendre des patterns dans les données",
            },
            {
                "question": "Qu'est-ce que le overfitting ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Quand un modèle apprend trop bien les données d'entraînement et performe mal sur de nouvelles données",
                    "B. Quand un modèle apprend trop lentement",
                    "C. Quand on utilise trop de données",
                    "D. Une erreur de programmation"
                ],
                "correction": "A - L'overfitting réduit la capacité de généralisation du modèle",
            },
        ],
        "intermediaire": [
            {
                "question": "Expliquez le concept de backpropagation",
                "type": "ChoixMultiple",
                "options": [
                    "A. Algorithme qui calcule les gradients pour ajuster les poids du réseau",
                    "B. Une technique pour retourner à la version précédente",
                    "C. Une méthode pour augmenter la vitesse",
                    "D. Cela n'existe pas"
                ],
                "correction": "A - Backpropagation est l'algorithme clé d'apprentissage des réseaux de neurones",
            },
            {
                "question": "Quelle est la différence entre supervised et unsupervised learning ?",
                "type": "ChoixMultiple",
                "options": [
                    "A. Supervised: données étiquetées, Unsupervised: pas d'étiquettes",
                    "B. C'est la même chose",
                    "C. Unsupervised est plus facile",
                    "D. Supervised n'existe plus"
                ],
                "correction": "A - Supervised learning utilise des données étiquetées, unsupervised découvre des patterns",
            },
            {
                "question": "Citez une application pratique de l'IA",
                "type": "ChoixMultiple",
                "options": [
                    "A. Reconnaissance d'images, chatbots, recommandations",
                    "B. L'IA n'a pas d'applications",
                    "C. Seulement pour les jeux vidéo",
                    "D. Uniquement en recherche"
                ],
                "correction": "A - L'IA a de nombreuses applications pratiques et utiles",
            },
        ],
        "avance": [
            {
                "question": "Décrivez comment vous déploieriez un modèle IA en production",
                "type": "QuestionOuverte",
                "correction": "Réponse attendue : conteneurs, monitoring, versioning, A/B testing, logs et alertes",
            },
        ]
    }
}

def get_questionnaire_for_domain(domain: str) -> dict:
    """Retourne le questionnaire adapté au domaine professionnel"""
    if domain in QUESTIONNAIRES_PAR_DOMAINE:
        return QUESTIONNAIRES_PAR_DOMAINE[domain]
    # Domaine par défaut pour Informatique
    return QUESTIONNAIRES_PAR_DOMAINE.get("Informatique & Développement")

def get_available_domains() -> list:
    """Retourne la liste des domaines disponibles"""
    return list(QUESTIONNAIRES_PAR_DOMAINE.keys())

def get_shuffled_questions(domain: str, num_questions: int = 5) -> list:
    """
    Retourne un ensemble de questions variées du domaine, mélangées pour éviter la répétition.
    """
    if domain not in QUESTION_POOLS:
        domain = "Informatique & Développement"

    pool = QUESTION_POOLS[domain]
    all_questions = []

    # Combiner les questions de tous les niveaux
    for level in pool.values():
        all_questions.extend(level)

    # Mélanger et sélectionner
    selected = random.sample(all_questions, min(num_questions, len(all_questions)))

    # Ajouter le numéro
    for i, q in enumerate(selected, 1):
        q["numero"] = i

    return selected
