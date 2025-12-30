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
⚠️ **PRINCIPE FONDAMENTAL**: Les questions ouvertes (QuestionOuverte, ListeOuverte) sont **LA SOURCE DE VÉRITÉ** pour évaluer le vrai niveau.
- Un utilisateur qui réussit les QCM mais échoue aux questions ouvertes est un **DÉBUTANT** (niveau 1-3)
- Un utilisateur qui excelle aux questions ouvertes mais échoue aux QCM a pu faire des erreurs d'inattention (niveau reste élevé)
- **SEULES les questions ouvertes révèlent la vraie compréhension conceptuelle**

Analyse chaque réponse pour identifier:
1. **PRIORITÉ 1**: La profondeur de compréhension dans les questions ouvertes (sens, cohérence, précision)
2. Les forces et faiblesses spécifiques en IA
3. Les lacunes de connaissances précises
4. Le style d'apprentissage (conceptuel vs pratique)
5. Les domaines IA à prioriser

📊 ANALYSE DÉTAILLÉE REQUISE:

A. NIVEAU (1-10) - MÉTHODE D'ÉVALUATION STRICTE:

**ÉTAPE 1 - ANALYSE DES QUESTIONS OUVERTES (POIDS 70%)**:
Examine CHAQUE question ouverte (QuestionOuverte, ListeOuverte):

Pour chaque réponse ouverte, évalue:
- **Sens et cohérence**: La réponse montre-t-elle une vraie compréhension du concept ?
- **Profondeur conceptuelle**: Utilise-t-elle les bons termes techniques ? Explique-t-elle le "pourquoi" ?
- **Précision**: Les exemples sont-ils pertinents ? Les explications sont-elles justes ?
- **Exhaustivité**: Pour les listes, a-t-elle mentionné les éléments clés ?

Scoring des questions ouvertes:
- Réponse vide ou hors-sujet: 0/10
- Réponse superficielle sans termes techniques: 2/10
- Réponse correcte mais incomplète: 5/10
- Réponse solide avec bons concepts: 7/10
- Réponse approfondie avec exemples et justifications: 10/10

Calcule la **moyenne des questions ouvertes** (ex: 6.5/10)

**ÉTAPE 2 - ANALYSE DES QCM (POIDS 30%)**:
- Score QCM: calcule le % de bonnes réponses
- Convertis en note /10

**ÉTAPE 3 - CALCUL FINAL**:
niveau = (moyenne_questions_ouvertes × 0.7) + (score_qcm × 0.3)

**RÈGLES DE PLAFONNEMENT**:
- Si moyenne questions ouvertes < 4/10 → niveau MAX = 3 (même avec 100% QCM)
- Si moyenne questions ouvertes < 6/10 → niveau MAX = 5
- Si réponses ouvertes vides ou incohérentes → niveau MAX = 2
- Si moyenne questions ouvertes > 8/10 → niveau MIN = 7 (même avec QCM faibles)

**RÈGLE DE COHÉRENCE AVEC COMPÉTENCES DÉCLARÉES**:
- Si l'utilisateur déclare des compétences avancées (ex: "CNN", "NLP", "Transformers", "Backpropagation") ET que la moyenne des questions ouvertes ≥ 6/10 → niveau MIN = 5 (intermédiaire)
- Si compétences très avancées (ex: "Attention Mechanisms", "Transfer Learning") ET moyenne des questions ouvertes ≥ 7/10 → niveau MIN = 7 (avancé)
- Si compétences avancées mais réponses ouvertes faibles (< 5/10) → ne PAS rehausser le niveau (cohérence prime sur déclaratif)

**EXEMPLES CONCRETS**:
- QCM: 90%, Questions ouvertes: vides → NIVEAU = 2 (débutant qui devine)
- QCM: 50%, Questions ouvertes: excellentes (8/10) → NIVEAU = 7 (expert distrait)
- QCM: 80%, Questions ouvertes: solides (7/10) → NIVEAU = 7
- QCM: 100%, Questions ouvertes: superficielles (4/10) → NIVEAU = 4

B. COMPÉTENCES (liste détaillée):
⚠️ **NE liste que les compétences démontrées dans les QUESTIONS OUVERTES**
- Si l'utilisateur explique bien les CNN dans une question ouverte → ajoute "CNN"
- Si l'utilisateur coche la bonne case sur les CNN mais ne peut pas expliquer → NE PAS ajouter "CNN"
- Sois spécifique: "Deep Learning", "Backpropagation", "Transfer Learning", "Attention Mechanisms"
- Maximum 5-7 compétences VRAIMENT maîtrisées

C. OBJECTIFS (texte détaillé):
- **Focus sur les lacunes révélées par les questions ouvertes**
- Si réponses ouvertes faibles → objectif = "Approfondir la compréhension conceptuelle"
- Propose un parcours progressif: théorie → pratique → projets
- Mentionne les concepts IA à renforcer avec exemples concrets

D. MOTIVATION (analyse psychologique):
- Analyse la **qualité de rédaction** des réponses ouvertes (pas juste le score)
- Réponses détaillées → forte motivation intrinsèque
- Réponses courtes/bâclées → motivation faible ou manque de temps
- Adapte le ton selon l'effort fourni

E. ENERGIE (1-10):
- **Base-toi sur la QUALITÉ des réponses ouvertes, pas juste si elles sont remplies**
- Réponses ouvertes détaillées et réfléchies → énergie 8-10
- Réponses ouvertes courtes mais présentes → énergie 5-7
- Réponses ouvertes vides ou "je ne sais pas" → énergie 1-3

F. PRÉFÉRENCES (objet détaillé):
- **themes**: Déduis des QUESTIONS OUVERTES quels thèmes IA l'intéressent vraiment
- **type_de_questions**: Si écart énorme entre QCM et questions ouvertes → note "preference_apparente_vs_reelle"
- **niveau_cible**: Basé sur l'écart actuel révélé par les questions ouvertes
- **style_apprentissage**: 
  - Bonnes réponses ouvertes théoriques → "theorique"
  - Mention d'exemples/projets dans réponses → "pratique"
  - Les deux → "mixte"
- **domaines_a_renforcer**: Domaines où réponses ouvertes étaient faibles/vides
- **points_forts**: Domaines où réponses ouvertes étaient excellentes

G. RECOMMANDATIONS (nouveau champ):
- **Si questions ouvertes faibles**: Recommande de renforcer les bases conceptuelles
- **Si QCM faibles mais questions ouvertes fortes**: Recommande de faire plus d'exercices pratiques
- 3-5 actions concrètes basées sur l'analyse des réponses ouvertes

📝 EXEMPLES D'ANALYSE SÉMANTIQUE DES RÉPONSES OUVERTES:

**Question**: "Expliquez le concept de backpropagation"
- ❌ Réponse vide → 0/10 → Compétence NON acquise
- ❌ "C'est un algorithme" → 2/10 → Compréhension superficielle
- ⚠️ "Ça sert à entraîner les réseaux de neurones" → 4/10 → Idée générale mais pas de détails
- ✅ "C'est un algorithme qui calcule les gradients en propageant l'erreur de la sortie vers l'entrée" → 7/10 → Bonne compréhension
- ✅✅ "Backpropagation utilise la règle de la chaîne pour calculer les dérivées partielles de la loss function par rapport à chaque poids, permettant l'optimisation par descente de gradient" → 10/10 → Maîtrise complète

**Question**: "Citez 3 types de réseaux de neurones"
- ❌ Réponse vide → 0/10
- ❌ "réseaux, neurones, IA" → 1/10 → Hors sujet
- ⚠️ "CNN, RNN" → 5/10 → 2/3 correct mais incomplet
- ✅ "CNN (Convolutional), RNN (Recurrent), Transformers" → 9/10 → Complet et précis
- ✅✅ "CNN pour images, RNN pour séquences, Transformers pour NLP moderne avec attention" → 10/10 → Complet avec contexte

🎨 FORMAT DE SORTIE:
Retourne un JSON valide avec cette structure exacte:

{{
  "niveau": <int 1-10>,
  "niveau_reel": "débutant|intermédiaire|avancé|expert",
  "score_questions_ouvertes": <float 0-10>,
  "score_qcm": <float 0-10>,
  "comprehension_profonde": "faible|moyenne|bonne|excellente",
  "capacite_explication": "faible|moyenne|bonne|excellente",
  "competences": ["compétence1", "compétence2", ...],
  "objectifs": "texte détaillé des objectifs personnalisés",
  "motivation": "analyse de la motivation",
  "energie": <int 1-10>,
  "preferences": {{
    "themes": ["theme1", "theme2"],
    "style_apprentissage": "theorique|pratique|mixte",
    "domaines_a_renforcer": ["domaine1", "domaine2"],
    "points_forts": ["force1", "force2"]
  }},
  "recommandations": [
    "Recommandation concrète 1",
    "Recommandation concrète 2",
    "Recommandation concrète 3",
    "Recommandation concrète 4",
    "Recommandation concrète 5"
  ],
  "commentaires": "Analyse narrative personnalisée expliquant le niveau déterminé et les recommandations"
}}

⚠️ RAPPELS IMPORTANTS:
1. **Les questions ouvertes sont LA source de vérité** - ne te laisse pas tromper par un bon score QCM
2. Sois strict dans l'évaluation des réponses ouvertes - vide = 0, superficielle = 2-3
3. Les recommandations doivent être actionnables et spécifiques aux lacunes identifiées
4. Le champ "commentaires" doit expliquer pourquoi tu as attribué ce niveau
"""


def analyze_profile_with_llm(user_json: str, evaluation_json: str) -> str:
    """
    Analyse le profil d'un utilisateur basé sur ses résultats de quiz avec un LLM.

    Args:
        user_json: JSON string contenant les données de l'utilisateur
        evaluation_json: JSON string contenant les résultats du quiz

    Returns:
        str: Réponse du LLM contenant l'analyse au format JSON
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=Config.OPENAI_API_KEY
    )

    prompt = ANALYZE_PROMPT.format(
        user_json=user_json,
        evaluation_json=evaluation_json
    )

    response = llm.invoke(prompt)
    return response.content

