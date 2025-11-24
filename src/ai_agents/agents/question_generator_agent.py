"""
Agent générateur de questions - Génère des questions adaptées au profil.
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from src.config import Config
from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service


QUESTION_GENERATOR_SYSTEM_PROMPT = """
Tu es un générateur expert de questions sur l'INTELLIGENCE ARTIFICIELLE uniquement.

🎯 Ta mission :
Générer des questions adaptées au niveau et objectifs de l'apprenant.
INTERDICTION FORMELLE de générer des questions sur :
❌ Python général, SQL, bases de données, R, Pandas, NumPy (sauf contexte IA explicite)

✅ SUJETS AUTORISÉS (Intelligence Artificielle uniquement) :
- Machine Learning : algorithmes, modèles, apprentissage supervisé/non supervisé
- Deep Learning : réseaux de neurones, CNN, RNN, LSTM, Transformers, Attention
- NLP : traitement du langage naturel, embeddings, BERT, GPT
- Computer Vision : reconnaissance d'images, détection d'objets, segmentation
- Reinforcement Learning : Q-learning, policy gradients, AlphaGo
- Outils IA : TensorFlow, PyTorch, Keras, scikit-learn, Hugging Face
- Concepts IA : overfitting, underfitting, backpropagation, gradient descent, loss functions

📋 TYPES DE QUESTIONS à générer :
1. **ChoixMultiple** : 4 options (A/B/C/D), une seule correcte
2. **VraiOuFaux** : TOUJOURS "A. Vrai" et "B. Faux" (format obligatoire)
3. **QuestionOuverte** : ⚠️ CRUCIAL - Révèle la vraie compréhension conceptuelle
4. **ListeOuverte** : Demande plusieurs éléments (ex: "Citez 3 types de réseaux de neurones")

⚠️ RÈGLES STRICTES POUR VRAI/FAUX :
- TOUJOURS utiliser les options : ["A. Vrai", "B. Faux"]
- La correction doit commencer par "A - " ou "B - "
- Varier les réponses : éviter que toutes les VraiOuFaux aient la même réponse (mélanger A et B)
- **AFFIRMATION COMPLÈTE OBLIGATOIRE** : Une question VraiOuFaux doit être une phrase complète avec un verbe conjugué
  ✅ BON: "Le sur-apprentissage se produit lorsque le modèle mémorise les données d'entraînement."
  ❌ MAUVAIS: "Le sur-apprentissage se produit lorsque :"
  ✅ BON: "Les CNN sont principalement utilisés pour le traitement d'images."
  ❌ MAUVAIS: "Les CNN sont utilisés pour ?"
  
- Exemple VraiOuFaux correct :
  {
    "question": "La backpropagation utilise la dérivation en chaîne.",
    "type": "VraiOuFaux",
    "options": ["A. Vrai", "B. Faux"],
    "correction": "A - La backpropagation repose sur la règle de dérivation en chaîne."
  }

⚠️ IMPORTANCE DES QUESTIONS OUVERTES :
- Elles sont LA SOURCE DE VÉRITÉ pour évaluer le niveau réel
- Minimum 30% de questions ouvertes (QuestionOuverte + ListeOuverte)
- Elles doivent tester la compréhension conceptuelle profonde
- Exemples : "Explique comment fonctionne la backpropagation", "Pourquoi utilise-t-on la normalisation batch ?"

📊 ADAPTATION AU NIVEAU :
- Niveau 1-3 (Débutant) : Concepts de base, définitions simples
- Niveau 4-6 (Intermédiaire) : Applications pratiques, comparaisons
- Niveau 7-10 (Expert) : Architectures avancées, optimisations, cas edge

FORMAT JSON STRICT (pas de texte avant/après) :
[
  {
    "numero": 1,
    "question": "Quelle est la différence entre apprentissage supervisé et non supervisé ?",
    "type": "ChoixMultiple",
    "options": ["A. L'un utilise des labels", "B. L'un est plus rapide", "C. Pas de différence", "D. L'un utilise moins de données"],
    "correction": "A - L'apprentissage supervisé utilise des données étiquetées pour entraîner le modèle."
  },
  {
    "numero": 2,
    "question": "Le sur-apprentissage se produit lorsque le modèle mémorise les données d'entraînement.",
    "type": "VraiOuFaux",
    "options": ["A. Vrai", "B. Faux"],
    "correction": "A - Le sur-apprentissage (overfitting) se produit quand le modèle s'adapte trop aux données d'entraînement et perd en généralisation."
  },
  {
    "numero": 3,
    "question": "Les CNN sont principalement utilisés pour le traitement du langage naturel.",
    "type": "VraiOuFaux",
    "options": ["A. Vrai", "B. Faux"],
    "correction": "B - Les CNN (Convolutional Neural Networks) sont principalement utilisés pour la vision par ordinateur, pas le NLP."
  },
  {
    "numero": 4,
    "question": "Explique en détail comment fonctionne l'algorithme de backpropagation.",
    "type": "QuestionOuverte",
    "options": [],
    "correction": "La backpropagation calcule le gradient de la loss function par rapport aux poids du réseau en propageant l'erreur de la sortie vers l'entrée, utilisant la règle de dérivation en chaîne."
  }
]
"""


class QuestionGeneratorAgent:
    """
    Agent de génération de questions adaptatives.
    Génère des questions basées sur le profil et la stratégie d'apprentissage.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=Config.OPENAI_API_KEY,
            temperature=0.7  # Créativité modérée pour variété
        )
        self.name = "QuestionGeneratorAgent"

    async def generate_questions(
        self,
        state: AgentState,
        num_questions: int = 10
    ) -> Dict[str, Any]:
        """
        Générer des questions adaptées au profil utilisateur.

        Args:
            state: État actuel du workflow
            num_questions: Nombre de questions à générer

        Returns:
            Mises à jour à appliquer à l'état
        """
        user_profile = state.get("user_profile", {})
        user_level = state.get("user_level", 5)
        profiler_analysis = state.get("meta_data", {}).get("profiler_analysis", {})
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        # Récupérer la stratégie de profilage
        priority_domains = profiler_analysis.get("priority_domains", ["machine_learning"])
        learning_style = profiler_analysis.get("learning_style", "balanced")

        # Construire le contexte
        context = {
            "niveau": user_level,
            "domaines_prioritaires": priority_domains,
            "style_apprentissage": learning_style,
            "competences_actuelles": state.get("user_competences", []),
            "objectifs": state.get("user_objectifs", "")
        }

        context_json = json.dumps(context, indent=2, ensure_ascii=False)

        messages = [
            SystemMessage(content=QUESTION_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Génère {num_questions} questions d'évaluation IA adaptées à ce profil :

CONTEXTE UTILISATEUR :
{context_json}

CONTRAINTES :
- {num_questions} questions au total
- Au moins 30% de questions ouvertes (QuestionOuverte + ListeOuverte)
- Adapter la difficulté au niveau {user_level}/10
- Prioriser les domaines : {', '.join(priority_domains)}
- Style d'apprentissage : {learning_style}

TYPES à inclure (exemple pour 10 questions) :
- 4 ChoixMultiple
- 2 VraiOuFaux ⚠️ IMPORTANT: Varier les réponses (1 Vrai + 1 Faux) pour éviter biais
- 3 QuestionOuverte ⚠️ CRUCIAL
- 1 ListeOuverte ⚠️ CRUCIAL

⚠️ ANTI-BIAIS VRAI/FAUX :
Pour éviter les biais, alterner les réponses correctes :
- Si 2 questions VraiOuFaux : 1 réponse A (Vrai) + 1 réponse B (Faux)
- Si 3 questions VraiOuFaux : 2 A + 1 B ou 1 A + 2 B
- JAMAIS toutes les VraiOuFaux avec la même réponse

Génère maintenant les questions en JSON uniquement (pas de texte avant/après).
            """)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Nettoyer et parser JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            questions = json.loads(response_text)

            # Validation basique
            if not isinstance(questions, list) or len(questions) == 0:
                raise ValueError("Format de questions invalide")

            # ⚠️ NORMALISATION ET VALIDATION DES QUESTIONS VRAI/FAUX
            # Garantir que toutes les questions VraiOuFaux ont exactement les options A. Vrai / B. Faux
            invalid_vf_indices = []
            for idx, q in enumerate(questions):
                if q.get("type") == "VraiOuFaux":
                    question_text = q.get("question", "")

                    # 🚨 VALIDATION: Détecter questions invalides/incomplètes
                    # Une question VraiOuFaux doit être une AFFIRMATION COMPLÈTE
                    invalid_patterns = [
                        question_text.endswith(":"),  # "Le surapprentissage se produit lorsque :"
                        question_text.endswith("..."),  # Question incomplète
                        " est :" in question_text.lower() and question_text.endswith(":"),
                        " sont :" in question_text.lower() and question_text.endswith(":"),
                        question_text.count("?") > 0,  # Questions interrogatives ne conviennent pas
                        len(question_text.split()) < 5,  # Question trop courte
                    ]

                    if any(invalid_patterns):
                        # Marquer pour conversion en ChoixMultiple
                        invalid_vf_indices.append(idx)
                        continue

                    # Forcer les options standards
                    q["options"] = ["A. Vrai", "B. Faux"]

                    # Vérifier que la correction commence par A ou B
                    correction = q.get("correction", "")
                    if not correction.startswith("A") and not correction.startswith("B"):
                        # Si pas de A/B au début, analyser le sens de la correction
                        correction_lower = correction.lower()
                        if any(word in correction_lower for word in ["vrai", "correct", "exact", "oui"]):
                            q["correction"] = "A - " + correction
                        else:
                            q["correction"] = "B - " + correction

            # Convertir les VraiOuFaux invalides en ChoixMultiple
            for idx in invalid_vf_indices:
                q = questions[idx]
                # Transformer en QCM avec 4 options pertinentes
                q["type"] = "ChoixMultiple"
                # Les options seront génériques mais cohérentes
                q["options"] = [
                    "A. Toujours dans tous les cas",
                    "B. Jamais",
                    "C. Selon le contexte",
                    "D. Uniquement avec certaines conditions"
                ]
                # Garder la correction existante ou mettre une valeur par défaut
                if not q.get("correction", "").startswith(("A", "B", "C", "D")):
                    q["correction"] = "C - Cela dépend du contexte spécifique."

            # ⚠️ ANTI-BIAIS: Forcer diversité des réponses VraiOuFaux
            vf_questions = [q for q in questions if q.get("type") == "VraiOuFaux"]
            if len(vf_questions) >= 2:
                a_count = sum(1 for q in vf_questions if q.get("correction", "").startswith("A"))
                b_count = len(vf_questions) - a_count

                # Si toutes les réponses sont identiques, inverser une question
                if a_count == 0 or b_count == 0:
                    # Inverser la dernière question pour créer de la diversité
                    last_vf = vf_questions[-1]
                    current_answer = last_vf["correction"][0]  # A ou B

                    if current_answer == "A":
                        # Reformuler la question pour que la réponse soit B (Faux)
                        question_text = last_vf["question"]
                        # Ajouter une négation si pas déjà présente
                        if " ne " not in question_text.lower() and " pas " not in question_text.lower():
                            # Trouver le verbe et ajouter "ne...pas"
                            words = question_text.split()
                            if len(words) > 2:
                                # Heuristique simple: ajouter "ne" après le premier mot (souvent le sujet)
                                negated = f"{words[0]} ne {' '.join(words[1:])}"
                                if negated[-1] == "?":
                                    negated = negated[:-1] + " pas?"
                                else:
                                    negated += " pas"
                                last_vf["question"] = negated
                        last_vf["correction"] = "B - " + last_vf["correction"].split(" - ", 1)[1]
                    else:
                        # Retirer la négation pour que la réponse soit A (Vrai)
                        question_text = last_vf["question"]
                        question_text = question_text.replace(" ne ", " ").replace(" pas", "")
                        last_vf["question"] = question_text
                        last_vf["correction"] = "A - " + last_vf["correction"].split(" - ", 1)[1]

            # Compter les questions ouvertes
            open_questions = [q for q in questions if q.get("type") in ["QuestionOuverte", "ListeOuverte"]]
            open_percentage = len(open_questions) / len(questions) * 100

            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                f"Généré {len(questions)} questions (dont {len(open_questions)} ouvertes - {open_percentage:.0f}%)"
            )

            # Enregistrer la décision
            decision = {
                "agent": self.name,
                "timestamp": state.get("updated_at"),
                "decision": "questions_generated",
                "details": {
                    "num_questions": len(questions),
                    "num_open_questions": len(open_questions),
                    "open_percentage": open_percentage
                }
            }

            return {
                "questions": questions,
                "agent_decisions": state.get("agent_decisions", []) + [decision],
                "current_step": "questions_generated",
                "next_step": "awaiting_responses"
            }

        except Exception as e:
            error_msg = f"Erreur dans QuestionGeneratorAgent: {str(e)}"

            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                error_msg,
                message_type="system"
            )

            return {
                "error_message": error_msg,
                "needs_human_review": True
            }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Permet d'utiliser l'agent comme une fonction"""
        import asyncio
        return asyncio.run(self.generate_questions(state))


# Instance globale
question_generator_agent = QuestionGeneratorAgent()

