from __future__ import annotations
from langchain_openai import ChatOpenAI
import langchain
from src.config import Config

langchain.verbose = False
langchain.debug = False
langchain.llm_cache = False


ANALYZE_PROMPT = """
Tu es un expert en analyse de compétences IA. Analyse en profondeur les résultats du quiz pour créer un profil d'apprentissage détaillé et personnalisé.

DONNÉES UTILISATEUR:
{user_json}

RÉSULTATS DU QUIZ:
{evaluation_json}

🎯 MISSION CRITIQUE:
⚠️ **PRINCIPE D'ÉVALUATION ÉQUILIBRÉE**: Évalue le niveau de l'utilisateur en tenant compte de TOUS les indicateurs.
- Les questions ouvertes montrent la compréhension conceptuelle
- Les QCM montrent les connaissances théoriques
- **COMBINE les deux** pour une évaluation juste et encourageante
- **Sois GÉNÉREUX** dans l'évaluation - valorise les efforts et les connaissances partielles
- En cas de doute entre deux niveaux, **choisis le niveau SUPÉRIEUR**

⚠️ **ADAPTATION AU DOMAINE D'APPLICATION**:
L'IA s'applique différemment selon le domaine professionnel de l'utilisateur. Adapte ton évaluation :

**DOMAINES D'APPLICATION**:
1. **Marketing & Communication**: Utilisation de l'IA pour l'analyse de données clients, personnalisation, chatbots, génération de contenu
2. **Droit & Justice**: IA pour analyse de documents juridiques, recherche de jurisprudence, prédiction de décisions
3. **Santé & Médecine**: Diagnostic assisté par IA, analyse d'images médicales, médecine prédictive
4. **Finance & Comptabilité**: Analyse prédictive, détection de fraudes, trading algorithmique
5. **Éducation & Formation**: Personnalisation de l'apprentissage, évaluation automatique, tuteurs intelligents
6. **Informatique & Développement**: Développement de modèles IA, MLOps, architecture de systèmes IA
7. **Arts & Création**: Génération d'images, musique, écriture assistée par IA
8. **Sciences & Recherche**: Modélisation scientifique, analyse de données expérimentales
9. **Management & RH**: Recrutement assisté par IA, analyse de performance, prédiction d'attrition
10. **Agriculture & Environnement**: Optimisation des cultures, prédiction météo, monitoring environnemental

**RÈGLES D'ÉVALUATION SELON LE DOMAINE**:
- Pour un **non-informaticien** (marketing, droit, etc.): Ne pas attendre une maîtrise technique approfondie des algorithmes
  - Niveau 7-8 = Sait utiliser des outils IA efficacement, comprend les concepts clés, peut superviser des projets IA
  - Niveau 9-10 = Expert métier qui comprend profondément comment l'IA transforme son domaine
  
- Pour un **informaticien/développeur**: Attendre une compréhension technique plus approfondie
  - Niveau 7-8 = Peut implémenter et déployer des modèles IA, comprend les algorithmes
  - Niveau 9-10 = Peut concevoir des architectures IA complexes, faire de la recherche

**INDICES DU DOMAINE D'APPLICATION**:
- Statut utilisateur (Étudiant, Professeur, Professionnel)
- Mentions dans les réponses ouvertes (ex: "pour mon travail de marketing", "dans mon cabinet d'avocats")
- Type de questions posées ou d'intérêts exprimés

Analyse chaque réponse pour identifier:
1. **PRIORITÉ 1**: La profondeur de compréhension dans les questions ouvertes (sens, cohérence, précision)
2. **Le domaine d'application** probable de l'utilisateur
3. Les forces et faiblesses spécifiques en IA pour son domaine
4. Les lacunes de connaissances précises
5. Le style d'apprentissage (conceptuel vs pratique vs applicatif)
6. Les domaines IA à prioriser selon son profil professionnel

📊 ANALYSE DÉTAILLÉE REQUISE:

A. NIVEAU (1-10) - MÉTHODE D'ÉVALUATION STRICTE ADAPTÉE AU DOMAINE:

**ÉTAPE 1 - ANALYSE DES QUESTIONS OUVERTES (POIDS 70%)**:
Examine CHAQUE question ouverte (QuestionOuverte, ListeOuverte):

Pour chaque réponse ouverte, évalue:
- **Sens et cohérence**: La réponse montre-t-elle une vraie compréhension du concept ?
- **Profondeur conceptuelle**: Utilise-t-elle les bons termes ? Explique-t-elle le "pourquoi" ?
- **Précision**: Les exemples sont-ils pertinents ? Les explications sont-elles justes ?
- **Exhaustivité**: Pour les listes, a-t-elle mentionné les éléments clés ?
- **Application pratique**: Mentionne-t-elle des cas d'usage dans son domaine ?

Scoring des questions ouvertes (adapté au domaine) - **SOIS GÉNÉREUX**:
- Réponse vide: 0/10
- Réponse très courte mais pertinente: 4/10 ⬆️
- Réponse avec quelques termes techniques: 6/10 ⬆️
- Réponse correcte mais incomplète: 7/10 ⬆️
- Réponse solide avec bons concepts: 8/10 ⬆️
- Réponse approfondie avec exemples: 9/10
- Réponse complète avec justifications et vision: 10/10
- **BONUS**: +1 point si mention d'application dans son domaine professionnel

Calcule la **moyenne des questions ouvertes** (ex: 6.5/10)

**ÉTAPE 2 - ANALYSE DES QCM (POIDS 30%)**:
- Score QCM: calcule le % de bonnes réponses
- Convertis en note /10

**ÉTAPE 3 - CALCUL FINAL**:
niveau = (moyenne_questions_ouvertes × 0.7) + (score_qcm × 0.3)

**RÈGLES DE NIVEAU (GÉNÉREUSES ET ENCOURAGEANTES)**:

Pour **NON-INFORMATICIENS** (Marketing, Droit, Finance, etc.):
- Si moyenne questions ouvertes < 3/10 → niveau = 2-3 (novice/débutant)
- Si moyenne questions ouvertes 3-5/10 → niveau = 4-5 (apprenti/initié) ⬆️
- Si moyenne questions ouvertes 5-7/10 → niveau = 6-7 (intermédiaire/confirmé) ⬆️
- Si moyenne questions ouvertes 7-8/10 → niveau = 8 (avancé) ⬆️
- Si moyenne questions ouvertes > 8/10 → niveau = 9-10 (expert/maître) ⬆️

Pour **INFORMATICIENS/DÉVELOPPEURS**:
- Si moyenne questions ouvertes < 3/10 → niveau = 2-3 (débutant technique)
- Si moyenne questions ouvertes 3-5/10 → niveau = 4-5 (utilisateur d'outils IA) ⬆️
- Si moyenne questions ouvertes 5-7/10 → niveau = 6-7 (développeur IA) ⬆️
- Si moyenne questions ouvertes 7-8/10 → niveau = 8 (avancé) ⬆️
- Si moyenne questions ouvertes > 8/10 → niveau = 9-10 (expert/maître IA) ⬆️

**RÈGLE DE COHÉRENCE AVEC COMPÉTENCES DÉCLARÉES** (ENCOURAGEANTE):
- Si l'utilisateur déclare des compétences avancées → niveau MIN = 5 (intermédiaire) ⬆️
- Si compétences très avancées ET score global ≥ 50% → niveau MIN = 6 (confirmé) ⬆️
- **En cas de doute, privilégie le niveau SUPÉRIEUR** pour encourager l'utilisateur ⬆️
- Si QCM excellent (≥80%) mais questions ouvertes moyennes (≥5/10) → niveau MIN = 6 ⬆️

**EXEMPLES CONCRETS** (ÉVALUATION ENCOURAGEANTE):
- Avocat, QCM: 90%, Questions ouvertes: vides → NIVEAU = 3-4 (débutant avec potentiel) ⬆️
- Marketeur, QCM: 50%, Questions ouvertes: bonnes sur chatbots (6/10) → NIVEAU = 6-7 (confirmé métier IA) ⬆️
- Développeur, QCM: 80%, Questions ouvertes: solides sur CNN/RNN (7/10) → NIVEAU = 8 (avancé) ⬆️
- Étudiant info, QCM: 100%, Questions ouvertes: moyennes (5/10) → NIVEAU = 6 (intermédiaire solide) ⬆️
- Chimiste, QCM: 70%, Questions ouvertes: pertinentes (6/10) → NIVEAU = 6-7 (expert métier) ⬆️

B. DOMAINE D'APPLICATION (nouveau champ):
Identifie le domaine professionnel de l'utilisateur parmi:
- "Marketing & Communication"
- "Droit & Justice"
- "Santé & Médecine"
- "Finance & Comptabilité"
- "Éducation & Formation"
- "Informatique & Développement"
- "Arts & Création"
- "Sciences & Recherche"
- "Management & RH"
- "Agriculture & Environnement"
- "Général" (si non déterminé)

C. COMPÉTENCES (liste détaillée ADAPTÉE AU DOMAINE):
⚠️ **NE liste que les compétences démontrées dans les QUESTIONS OUVERTES**

Pour **NON-INFORMATICIENS**, privilégie:
- "Utilisation d'outils IA"
- "Compréhension des concepts IA"
- "Chatbots et assistants virtuels"
- "Analyse prédictive"
- "Personnalisation algorithmique"
- "Éthique de l'IA"
- "Prompt engineering"
- "Vision stratégique de l'IA"

Pour **INFORMATICIENS**, privilégie:
- "Machine Learning"
- "Deep Learning"
- "CNN", "RNN", "Transformers"
- "NLP", "Computer Vision"
- "MLOps", "Déploiement de modèles"
- "Architecture IA"
- "Optimisation d'algorithmes"

D. OBJECTIFS (texte détaillé PERSONNALISÉ AU DOMAINE):
- **Focus sur les cas d'usage du domaine professionnel**
- Si marketing → objectifs sur personnalisation, analyse client, génération de contenu
- Si droit → objectifs sur analyse de documents, recherche juridique
- Si développeur → objectifs sur implémentation de modèles, architecture
- Propose un parcours progressif adapté au domaine

E. MOTIVATION (analyse psychologique):
- Analyse la **qualité de rédaction** des réponses ouvertes (pas juste le score)
- Réponses détaillées → forte motivation intrinsèque
- Réponses courtes/bâclées → motivation faible ou manque de temps
- Adapte le ton selon l'effort fourni

F. ENERGIE (1-10):
- **Base-toi sur la QUALITÉ des réponses ouvertes**
- Réponses ouvertes détaillées et réfléchies → énergie 8-10
- Réponses ouvertes courtes mais présentes → énergie 5-7
- Réponses ouvertes vides ou "je ne sais pas" → énergie 1-3

G. PRÉFÉRENCES (objet détaillé):
- **domaine_application**: Le domaine professionnel identifié
- **themes**: Déduis des QUESTIONS OUVERTES quels thèmes IA l'intéressent
- **style_apprentissage**: "theorique|pratique|applicatif|mixte"
- **domaines_a_renforcer**: Selon son domaine professionnel
- **points_forts**: Selon son domaine professionnel

H. RECOMMANDATIONS (nouveau champ ADAPTÉ AU DOMAINE):
- **Si questions ouvertes faibles**: Recommande de renforcer les bases conceptuelles
- **Si non-informaticien**: Focus sur l'utilisation d'outils IA dans son métier
- **Si informaticien**: Focus sur l'implémentation technique
- 3-5 actions concrètes basées sur le domaine d'application

🎨 FORMAT DE SORTIE:
Retourne un JSON valide avec cette structure exacte:

{{
  "niveau": <int 1-10>,
  "niveau_reel": "novice|débutant|apprenti|initié|intermédiaire|confirmé|avancé|expert|maître|grand_maître",
  "domaine_application": "Marketing & Communication|Droit & Justice|...|Général",
  "score_questions_ouvertes": <float 0-10>,
  "score_qcm": <float 0-10>,
  "comprehension_profonde": "faible|moyenne|bonne|excellente",
  "capacite_explication": "faible|moyenne|bonne|excellente",
  "profil_utilisateur": "non_informaticien|informaticien|etudiant|chercheur",
  "competences": ["compétence1", "compétence2", ...],
  "objectifs": "texte détaillé des objectifs personnalisés selon le domaine",
  "motivation": "analyse de la motivation",
  "energie": <int 1-10>,
  "preferences": {{
    "domaine_application": "...",
    "themes": ["theme1", "theme2"],
    "style_apprentissage": "theorique|pratique|applicatif|mixte",
    "domaines_a_renforcer": ["domaine1", "domaine2"],
    "points_forts": ["force1", "force2"]
  }},
  "recommandations": [
    "Recommandation concrète 1 adaptée au domaine",
    "Recommandation concrète 2 adaptée au domaine",
    "Recommandation concrète 3 adaptée au domaine",
    "Recommandation concrète 4 adaptée au domaine",
    "Recommandation concrète 5 adaptée au domaine"
  ],
  "commentaires": "Analyse narrative personnalisée expliquant le niveau déterminé, le domaine d'application identifié et les recommandations"
}}

⚠️ PRINCIPES D'ÉVALUATION:
1. **Sois GÉNÉREUX et ENCOURAGEANT** - valorise les connaissances partielles ⬆️
2. **En cas de doute entre deux niveaux, choisis le SUPÉRIEUR** ⬆️
3. **Adapte l'évaluation au domaine professionnel** - chaque métier utilise l'IA différemment
4. **Combine QCM + questions ouvertes** - ne te base pas uniquement sur les questions ouvertes
5. **Les recommandations doivent être positives et actionnables** selon le domaine
6. **Le champ "commentaires" doit être encourageant** et expliquer le potentiel de l'utilisateur
"""


def analyze_profile_with_llm(user_json: str, evaluation_json: str, domaine: str = "Général") -> str:
    """
    Analyse le profil d'un utilisateur basé sur ses résultats de quiz avec un LLM.

    Args:
        user_json: JSON string contenant les données de l'utilisateur
        evaluation_json: JSON string contenant les résultats du quiz
        domaine: Le domaine d'études de l'utilisateur (Informatique, Droit, Marketing, etc.)

    Returns:
        str: Réponse du LLM contenant l'analyse au format JSON
    """
    from src.ai_agents.profiler.domain_context import get_domain_specific_prompt

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=Config.OPENAI_API_KEY
    )

    # Obtenir le prompt contextualisé au domaine
    domain_context = get_domain_specific_prompt(domaine)

    # Ajouter le contexte domaine au prompt
    prompt_with_domain = ANALYZE_PROMPT + f"\n\n🎯 CONTEXTE DOMAINE:\n{domain_context}"

    prompt = prompt_with_domain.format(
        user_json=user_json,
        evaluation_json=evaluation_json
    )

    response = llm.invoke(prompt)
    return response.content

