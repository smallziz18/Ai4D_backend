from langchain_ollama import ChatOllama
import langchain
from langchain_openai import ChatOpenAI

from src.config import Config

langchain.verbose = False
langchain.debug = False
langchain.llm_cache = False
from src.users.schema import UtilisateurRead

# Prompt optimisé pour une génération plus rapide
BASE_PROMPT = """
Tu es un générateur de quiz sur l'INTELLIGENCE ARTIFICIELLE uniquement.

🚨 RÈGLE ABSOLUE 🚨
Tu dois créer 10 questions EXCLUSIVEMENT sur l'Intelligence Artificielle.
INTERDICTION FORMELLE de poser des questions sur :
❌ Python (sauf libraries IA : TensorFlow, PyTorch, Keras, scikit-learn)
❌ SQL, bases de données, ETL, Data Engineering
❌ R, statistiques générales
❌ Pandas, NumPy (sauf dans un contexte IA explicite)
❌ Développement web, DevOps, Cloud

✅ SUJETS AUTORISÉS (Intelligence Artificielle uniquement) :
- Machine Learning : algorithmes, modèles, apprentissage supervisé/non supervisé
- Deep Learning : réseaux de neurones, CNN, RNN, LSTM, Transformers
- NLP (Natural Language Processing) : traitement du langage naturel
- Computer Vision : reconnaissance d'images, détection d'objets
- Reinforcement Learning : apprentissage par renforcement
- Outils IA : TensorFlow, PyTorch, Keras, scikit-learn, Hugging Face
- Concepts IA : overfitting, underfitting, backpropagation, gradient descent
- Applications IA : chatbots, reconnaissance vocale, systèmes de recommandation

PROFIL UTILISATEUR (pour adapter la difficulté uniquement) :
- Statut: {status}
- Compétences: {competences}
- Objectif: {objectifs_apprentissage}
- Niveau: {niveau_technique}/10

TYPES DE QUESTIONS :
1-2: ChoixMultiple (4 options A/B/C/D)
3-4: QuestionOuverte (pas d'options)
5-6: ListeOuverte (pas d'options)
7-8: ChoixMultiple (4 options A/B/C/D)

FORMAT JSON STRICT (pas de texte avant/après) :
[
  {{
    "numero": 1,
    "question": "Quelle est la différence entre apprentissage supervisé et non supervisé ?",
    "type": "ChoixMultiple",
    "options": ["A. L'un utilise des labels", "B. L'un est plus rapide", "C. Pas de différence", "D. L'un utilise moins de données"],
    "correction": "A - L'apprentissage supervisé utilise des données étiquetées."
  }}
]

EXEMPLES VALIDES :
✅ "Qu'est-ce qu'un neurone artificiel ?"
✅ "Comment fonctionne la rétropropagation ?"
✅ "Citez 3 architectures de réseaux de neurones"
✅ "Quelle est la fonction d'activation la plus utilisée ?"

EXEMPLES INVALIDES :
❌ "Qu'est-ce qu'un DataFrame en Pandas ?"
❌ "Comment faire une jointure SQL ?"
❌ "Qu'est-ce qu'un ETL ?"

GÉNÈRE MAINTENANT 10 QUESTIONS IA (JSON uniquement) :
"""

def generate_profile_question(user: UtilisateurRead) -> str:
    """Génère 10 questions personnalisées rapidement."""
    prompt = BASE_PROMPT.format(
        status=user.status,
        competences=", ".join(user.competences or ["Aucune"]),
        objectifs_apprentissage=user.objectifs_apprentissage or "Non spécifié",
        niveau_technique=user.niveau_technique or 5
    )

    # Configuration LLM optimisée pour la vitesse
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Corrigé : gpt-5-mini n'existe pas
        api_key=Config.OPENAI_API_KEY,
        temperature=0.7
    )
    question = llm.invoke(prompt)
    return question.content

# Remplacer les types pour interdire VraiOuFaux
ALLOWED_TYPES = [
    "ChoixMultiple",
    "QuestionOuverte",
    "ListeOuverte",
]

SYSTEM_RULES = {
    "interdictions": [
        "INTERDICTION ABSOLUE des questions VraiOuFaux (A/B).",
        "Ne jamais produire de type 'VraiOuFaux'.",
    ],
    "types_autorises": ALLOWED_TYPES,
    "ratio_min_ouvertes": 0.4,
}
