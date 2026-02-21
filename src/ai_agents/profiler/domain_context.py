"""
Adaptateur de prompt LLM selon le domaine d'études.
Contextualise l'analyse du profil pour chaque domaine.
"""

def get_domain_specific_prompt(domaine: str) -> str:
    """
    Génère un prompt LLM contextualisé au domaine de l'utilisateur.

    Args:
        domaine: Le domaine d'études (Informatique, Droit, Marketing, etc.)

    Returns:
        Un prompt spécialisé pour analyser le profil de l'utilisateur
    """

    domain_prompts = {
        "Informatique": """
Tu es un expert en analyse de profil pour les développeurs et informaticiens.
Analyse le profil fourni avec les critères suivants:

1. NIVEAU TECHNIQUE: Évalue le niveau de programmation, architecture système, et frameworks
2. EXPÉRIENCE IA/ML: Évalue la connaissance en machine learning, deep learning, frameworks (TensorFlow, PyTorch)
3. COMPÉTENCES SPÉCIALISÉES: Détecte les compétences avancées (Transformers, CNN, RNN, Reinforcement Learning)
4. OBJECTIFS PROFESSIONNELS: Alignement avec la carrière en tech

Le niveau doit refléter:
- 1-2: Novice/Débutant (aucune ou très peu d'expérience en programmation)
- 3-4: Apprenti/Initié (connaissances basiques, peut écrire du code simple)
- 5-6: Intermédiaire/Confirmé (peut concevoir des solutions, comprend les concepts avancés)
- 7-8: Avancé/Expert (maîtrise les architectures complexes, peut optimiser)
- 9-10: Maître/Grand Maître (expert reconnu, contribution à l'innovation)
""",

        "Data Science": """
Tu es un expert en analyse de profil pour les data scientists et analystes de données.
Analyse le profil fourni avec les critères suivants:

1. COMPÉTENCES STATISTIQUES: Évalue la connaissance en statistiques, probabilités, tests d'hypothèse
2. PROGRAMMATION POUR LA DATA: Python, R, SQL, manipulation de données
3. MACHINE LEARNING: Compréhension des algorithmes, feature engineering, évaluation de modèles
4. OUTILS DATA: Pandas, NumPy, Scikit-learn, matplotlib, etc.
5. PROJETS DATA: Expérience avec des datasets réels, cas d'usage métier

Le niveau doit refléter la progression de novice à expert en science des données.
""",

        "Droit": """
Tu es un expert en analyse de profil pour les professionnels du droit.
Analyse le profil fourni avec les critères suivants:

1. SPÉCIALISATION JURIDIQUE: Quel domaine du droit (civil, pénal, commercial, IP, etc.)
2. CONNAISSANCE DE L'IA EN DROIT: Awareness des impacts légaux et réglementaires de l'IA
3. INTÉRÊT POUR IA & LÉGALITÉ: RGPD, lois sur l'IA, responsabilité légale, éthique
4. OBJECTIFS PROFESSIONNELS: Utilisation pratique de l'IA dans la pratique juridique
5. NIVEAU TECHNIQUE: Compréhension basique ou avancée des systèmes techniques

Le niveau reflète l'expertise en "IA appliquée au droit" et la capacité à conseiller sur les enjeux légaux de l'IA.
""",

        "Marketing": """
Tu es un expert en analyse de profil pour les spécialistes du marketing et de la communication.
Analyse le profil fourni avec les critères suivants:

1. TYPE DE MARKETING: Digital, content, analytics, automation, AI-driven
2. EXPÉRIENCE AVEC L'IA: Outils de recommandation, segmentation, personnalisation, chatbots
3. DATA & ANALYTICS: Compréhension des KPIs, Google Analytics, A/B testing, prédiction
4. STRATÉGIE DE CONTENU: Utilisation de l'IA pour génération, optimisation, ciblage
5. OUTILS MARKETING: CRM, automation platforms, analytics tools

Le niveau reflète la maturité en utilisation de l'IA pour optimiser les campagnes marketing.
""",

        "Médecine": """
Tu es un expert en analyse de profil pour les professionnels de la santé et médecins.
Analyse le profil fourni avec les critères suivants:

1. SPÉCIALITÉ MÉDICALE: Quelle spécialité ou domaine (diagnostic, pharmacologie, épidémiologie, recherche)
2. CONNAISSANCE DE L'IA MÉDICALE: Awareness de l'IA en diagnostic, traitement, prédiction
3. APPLICATIONS CLINIQUES: Intérêt pour imagerie IA, prédiction de prédispositions, outils décisionnels
4. ENJEUX ÉTHIQUES: Compréhension de la responsabilité, biais, éthique médicale avec l'IA
5. NIVEAU TECHNIQUE: Compréhension basique ou avancée de comment fonctionnent les modèles

Le niveau reflète l'expertise pour intégrer l'IA dans la pratique médicale de manière responsable.
""",

        "Chimie": """
Tu es un expert en analyse de profil pour les chimistes et chercheurs.
Analyse le profil fourni avec les critères suivants:

1. DOMAINE DE CHIMIE: Organique, inorganique, analytique, chimie computationnelle
2. MODÉLISATION & SIMULATION: Expérience avec outils de modélisation moléculaire
3. IA POUR LA CHIMIE: Prédiction de propriétés, design de molécules, optimisation
4. TOOLS INFORMATIQUES: Python, packages scientifiques, machine learning pour chimie
5. RECHERCHE: Expérience avec données expérimentales ou computationnelles

Le niveau reflète la capacité à utiliser l'IA pour accélérer la découverte chimique.
""",

        "Physique": """
Tu es un expert en analyse de profil pour les physiciens et chercheurs.
Analyse le profil fourni avec les critères suivants:

1. DOMAINE DE PHYSIQUE: Mécanique, thermodynamique, électromagnétisme, astrophysique, quantique
2. MODÉLISATION NUMÉRIQUE: Expérience avec simulations, équations différentielles
3. IA POUR LA PHYSIQUE: Neural networks pour prédiction, optimization, inverse problems
4. PROGRAMMING SCIENTIFIQUE: Python, NumPy, TensorFlow/PyTorch pour applications physiques
5. RECHERCHE: Gestion de données volumineuses, optimisation expérimentale

Le niveau reflète la capacité à appliquer l'IA à des problèmes physiques complexes.
""",

        "Économie": """
Tu es un expert en analyse de profil pour les économistes et analystes financiers.
Analyse le profil fourni avec les critères suivants:

1. DOMAINE ÉCONOMIQUE: Macro, micro, secteur financier, econométrie
2. ANALYSE DE DONNÉES: Statistiques, modèles économétriques, séries temporelles
3. PRÉDICTION & FORECASTING: Modèles de prédiction économique, machine learning
4. OUTILS: Python, R, Excel avancé, bases de données économiques
5. APPLICATIONS: Prédiction de marché, analyse de risque, optimisation de portefeuille

Le niveau reflète la capacité à construire et interpréter des modèles économiques prédictifs.
""",

        "Général": """
Tu es un expert en profilage d'utilisateurs dans le domaine de l'IA et apprentissage automatique.
Analyse le profil fourni avec les critères suivants:

1. CONNAISSANCE GÉNÉRALE DE L'IA: Concepts fondamentaux, types d'apprentissage, applications
2. EXPÉRIENCE PRATIQUE: Projets, outils utilisés, frameworks pratiqués
3. COMPÉTENCES TECHNIQUES: Programmation, statistiques, data engineering
4. OBJECTIFS PERSONNELS: Motivation, directions souhaitées
5. NIVEAU GLOBAL: Estimation holistique du niveau de compétence

Le niveau doit être équilibré et refléter une progression générale en IA/ML.
"""
    }

    return domain_prompts.get(domaine, domain_prompts["Général"])


def get_domain_specific_recommendations(domaine: str, niveau: int, competences: list) -> list:
    """
    Génère des recommandations d'apprentissage contextualisées au domaine et niveau.

    Args:
        domaine: Le domaine d'études
        niveau: Le niveau (1-10)
        competences: Les compétences détectées

    Returns:
        Une liste de recommandations personalisées
    """

    recommendations = {
        "Informatique": {
            "beginner": [
                "📚 Débuter avec les fondamentaux: variables, boucles, conditions (Python ou JavaScript)",
                "🎯 Apprendre la programmation orientée objet (POO)",
                "💻 Pratiquer avec des petits projets (calculatrices, jeux simples)",
                "🔗 Explorer les structures de données (listes, dictionnaires, arbres)"
            ],
            "intermediate": [
                "🤖 Introduire les bases du machine learning avec scikit-learn",
                "📊 Apprendre pandas pour la manipulation de données",
                "🧠 Explorer les réseaux de neurones avec TensorFlow/Keras",
                "🔬 Participer à des projets open source"
            ],
            "advanced": [
                "🏗️ Maîtriser l'architecture de systèmes distribués",
                "🚀 Optimiser les modèles ML pour la production",
                "🎯 Explorer le reinforcement learning et les agents IA",
                "📈 Approfondir les transformers et NLP"
            ]
        },
        "Droit": {
            "beginner": [
                "📖 Comprendre les bases de l'IA et comment elle fonctionne",
                "⚖️ Étudier le RGPD et les lois actuelles sur la protection des données",
                "📋 Apprendre les cas d'usage juridiques de l'IA (contrats, recherche)",
                "🔍 Suivre l'évolution des régulations gouvernementales"
            ],
            "intermediate": [
                "📚 Approfondir les cadres légaux émergents (AI Act EU, etc.)",
                "⚖️ Étudier les enjeux de responsabilité et d'accountability",
                "💡 Analyser les cas limites : discrimination, propriété intellectuelle",
                "🌐 Comprendre la gouvernance de l'IA"
            ],
            "advanced": [
                "📋 Rédiger des policies et guidelines pour l'utilisation d'IA",
                "🏛️ Conseiller sur les implications légales d'IA complexes",
                "🔬 Participer à l'élaboration de nouvelles régulations",
                "🌍 Contribuer à la standardisation internationale"
            ]
        },
        "Marketing": {
            "beginner": [
                "📊 Apprendre les bases de segmentation et clustering",
                "🎯 Découvrir les outils d'IA marketing (HubSpot, Marketo)",
                "📈 Comprendre les KPIs et analytics",
                "💬 Explorer la personnalisation de contenu"
            ],
            "intermediate": [
                "🤖 Mettre en place de l'automation avec l'IA",
                "📊 Analyser des données de campagne avec Python/pandas",
                "🔮 Apprendre la prédiction de churn et la scoring",
                "💡 Optimiser les campagnes avec A/B testing"
            ],
            "advanced": [
                "🎯 Concevoir des systèmes de recommandation",
                "🧠 Utiliser le deep learning pour le NLP marketing",
                "🚀 Implémenter l'attribution multi-canal avec ML",
                "📡 Créer des modèles prédictifs de customer lifetime value"
            ]
        },
        "Médecine": {
            "beginner": [
                "📚 Comprendre les bases du machine learning en santé",
                "🏥 Étudier les applications cliniques actuelles de l'IA",
                "⚖️ Apprendre les enjeux éthiques et réglementaires",
                "📊 Découvrir les datasets médicaux publics"
            ],
            "intermediate": [
                "🖼️ Approfondir l'IA en imagerie médicale (IRM, CT, rayons X)",
                "🔮 Étudier les modèles de prédiction de diagnostic",
                "💊 Explorer la découverte de médicaments par IA",
                "📈 Apprendre la gestion de données patients (sécurité, privacy)"
            ],
            "advanced": [
                "🧬 Maîtriser les applications en génomique et médecine personnalisée",
                "🏥 Concevoir des systèmes d'aide à la décision clinique",
                "🔬 Contribuer à la recherche en IA médicale",
                "🌍 Développer des solutions pour les régions sous-desservies"
            ]
        },
        "Chimie": {
            "beginner": [
                "📚 Apprendre les bases de la chimie computationnelle",
                "🧪 Découvrir les outils de modélisation moléculaire",
                "📊 Comprendre comment l'IA peut aider à prédire les propriétés",
                "💻 Apprendre Python pour la chimie"
            ],
            "intermediate": [
                "🧬 Étudier le design de molécules assisté par IA",
                "📊 Utiliser le machine learning pour prédire les propriétés chimiques",
                "🔬 Explorer les datasets de chimie (PubChem, ChEMBL)",
                "🤖 Apprendre les réseaux de neurones pour chimie"
            ],
            "advanced": [
                "🧪 Maîtriser la génération de nouvelles molécules (GANs, diffusion)",
                "⚡ Optimiser les réactions chimiques avec RL",
                "🔬 Contribuer à la découverte de nouveaux matériaux",
                "🌍 Appliquer l'IA à des enjeux durabilité/environnement"
            ]
        },
        "Physique": {
            "beginner": [
                "📚 Apprendre les bases de la simulation numérique",
                "🧮 Comprendre les équations différentielles et leur résolution",
                "📊 Découvrir comment l'IA accélère la modélisation",
                "💻 Apprendre Python pour la physique"
            ],
            "intermediate": [
                "🧠 Utiliser les réseaux de neurones pour les équations différentielles",
                "⚡ Apprendre la mécanique computationnelle avec IA",
                "📊 Explorer les inverse problems avec machine learning",
                "🔬 Analyser des données expérimentales complexes"
            ],
            "advanced": [
                "🎯 Maîtriser les physics-informed neural networks (PINNs)",
                "🚀 Optimiser les expériences avec machine learning",
                "🔬 Découvrir de nouveaux phénomènes avec l'IA",
                "🌌 Appliquer à l'astrophysique et données cosmologiques"
            ]
        },
        "Économie": {
            "beginner": [
                "📊 Apprendre les bases de l'analyse statistique des données",
                "💹 Comprendre les séries temporelles",
                "📈 Découvrir les outils de base (Excel, Google Sheets avancé)",
                "💻 Apprendre Python pour l'économie"
            ],
            "intermediate": [
                "📊 Maîtriser les modèles économétriques",
                "🔮 Apprendre la prédiction avec machine learning",
                "💹 Analyser les données de marché et bourse",
                "🤖 Utiliser l'IA pour l'optimisation de portefeuille"
            ],
            "advanced": [
                "🧠 Maîtriser les modèles deep learning pour les séries temporelles",
                "💡 Concevoir des systèmes de trading basés sur IA",
                "📊 Analyser les risques systémiques avec IA",
                "🌍 Contribuer aux nouveaux models d'économie comportementale"
            ]
        },
        "Général": {
            "beginner": [
                "📚 Suivre un cours fondamental en machine learning (Coursera, etc.)",
                "💻 Apprendre Python et les bases de la programmation",
                "📊 Comprendre les concepts clés: données, modèles, entraînement",
                "🎯 Identifier vos domaines d'intérêt"
            ],
            "intermediate": [
                "🤖 Pratiquer avec des projets réels sur Kaggle",
                "📊 Approfondir les algorithmes: régression, classification, clustering",
                "🧠 Découvrir le deep learning",
                "📈 Apprendre l'évaluation et l'optimisation de modèles"
            ],
            "advanced": [
                "🚀 Maîtriser les architectures modernes (Transformers, etc.)",
                "📊 Deployer des modèles en production",
                "🔬 Contribuer à la recherche en IA",
                "🌍 Appliquer l'IA à des problèmes réels complexes"
            ]
        }
    }

    # Déterminer la catégorie de niveau
    if niveau <= 2:
        level_key = "beginner"
    elif niveau <= 5:
        level_key = "intermediate"
    else:
        level_key = "advanced"

    # Récupérer les recommandations
    domain_recs = recommendations.get(domaine, recommendations["Général"])
    return domain_recs.get(level_key, [])

