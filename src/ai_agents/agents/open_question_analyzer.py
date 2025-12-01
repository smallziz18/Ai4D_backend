"""
Analyseur approfondi de questions ouvertes avec GPT-4.
Évalue le sens, la profondeur et la qualité des réponses ouvertes.
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from src.config import Config


OPEN_QUESTION_ANALYSIS_PROMPT = """
Tu es un expert en évaluation pédagogique spécialisé en Intelligence Artificielle.

🎯 Ta mission :
Analyser en profondeur la réponse d'un apprenant à une question ouverte sur l'IA.

⚠️ PRINCIPE : Les questions ouvertes révèlent le VRAI niveau de compréhension.

📊 CRITÈRES D'ÉVALUATION (chaque critère sur 10) :

1. **Compréhension du concept** (0-10)
   - 0-2 : Aucune compréhension / Réponse hors-sujet
   - 3-4 : Compréhension très superficielle
   - 5-6 : Compréhension de base correcte
   - 7-8 : Bonne compréhension avec détails
   - 9-10 : Compréhension approfondie et nuancée

2. **Profondeur d'analyse** (0-10)
   - 0-2 : Réponse de surface, définition Wikipedia
   - 3-4 : Quelques détails mais reste superficiel
   - 5-6 : Explique le "comment" de manière claire
   - 7-8 : Explique le "pourquoi" et fait des liens
   - 9-10 : Analyse critique avec implications

3. **Exemples concrets** (0-10)
   - 0-2 : Aucun exemple ou exemples incorrects
   - 3-4 : Exemples vagues ou génériques
   - 5-6 : Exemples corrects mais basiques
   - 7-8 : Exemples pertinents et bien expliqués
   - 9-10 : Exemples avancés avec cas d'usage réels

4. **Clarté de l'explication** (0-10)
   - 0-2 : Confus, incohérent ou incompréhensible
   - 3-4 : Structure faible, termes mal utilisés
   - 5-6 : Clair mais pourrait être mieux structuré
   - 7-8 : Bien structuré avec vocabulaire correct
   - 9-10 : Explication impeccable, pédagogique

🎓 ESTIMATION DU NIVEAU RÉEL :
Basé sur le score global (moyenne des 4 critères) :
- 0-2.5 : Débutant absolu (niveau 1-2)
- 2.5-4 : Débutant (niveau 2-3)
- 4-5.5 : Intermédiaire bas (niveau 4-5)
- 5.5-7 : Intermédiaire (niveau 5-6)
- 7-8 : Intermédiaire avancé (niveau 7)
- 8-9 : Avancé (niveau 8-9)
- 9-10 : Expert (niveau 10)

💬 FEEDBACK CONSTRUCTIF :
- Sois précis sur ce qui est bien / ce qui manque
- Donne des pistes concrètes d'amélioration
- Encourage l'apprenant tout en étant honnête

FORMAT JSON STRICT :
{
  "scores": {
    "comprehension": 7,
    "profondeur": 6,
    "exemples": 5,
    "clarte": 7
  },
  "score_global": 6.25,
  "niveau_reel_estime": 6,
  "niveau_label": "Intermédiaire",
  "feedback": "Bonne compréhension de base du concept de backpropagation. Tu expliques correctement le principe de propagation de l'erreur. Cependant, il manque des détails sur la dérivation en chaîne et l'algorithme du gradient. Ajouter un exemple concret (ex: réseau à 2 couches) rendrait l'explication plus claire.",
  "points_forts": [
    "Bonne utilisation du vocabulaire technique",
    "Explication claire du flow avant-arrière"
  ],
  "points_amelioration": [
    "Détailler le rôle de la dérivation en chaîne",
    "Ajouter un exemple numérique simple",
    "Expliquer la mise à jour des poids"
  ],
  "suggestions": [
    "Regarder une vidéo animée sur la backpropagation pour visualiser le processus",
    "Implémenter un petit réseau from scratch pour comprendre les calculs",
    "Lire sur l'historique : algorithme de Rumelhart, Hinton et Williams (1986)"
  ]
}
"""


class OpenQuestionAnalyzer:
    """Analyseur approfondi de questions ouvertes avec GPT-4."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",  # GPT-4 pour analyse de qualité
            api_key=Config.OPENAI_API_KEY,
            temperature=0.3  # Peu de créativité, plus de précision
        )

    async def analyze_open_question(
        self,
        question: str,
        user_answer: str,
        expected_answer: str = None
    ) -> Dict[str, Any]:
        """
        Analyse une réponse à une question ouverte en profondeur.

        Args:
            question: La question posée
            user_answer: La réponse de l'utilisateur
            expected_answer: Réponse attendue/correction (optionnel)

        Returns:
            Dict avec scores détaillés et feedback
        """
        # Cas de réponse vide
        if not user_answer or not str(user_answer).strip():
            return {
                "scores": {
                    "comprehension": 0,
                    "profondeur": 0,
                    "exemples": 0,
                    "clarte": 0
                },
                "score_global": 0.0,
                "niveau_reel_estime": 1,
                "niveau_label": "Débutant absolu",
                "feedback": "Aucune réponse fournie. Il est essentiel de répondre aux questions ouvertes pour évaluer ton niveau réel.",
                "points_forts": [],
                "points_amelioration": ["Prendre le temps de formuler une réponse"],
                "suggestions": ["Réessayer en expliquant avec tes propres mots"]
            }

        context = ""
        if expected_answer:
            context = f"\n\nRÉPONSE ATTENDUE (pour référence) :\n{expected_answer}"

        messages = [
            SystemMessage(content=OPEN_QUESTION_ANALYSIS_PROMPT),
            HumanMessage(content=f"""
Analyse cette réponse à une question ouverte d'évaluation en IA.

QUESTION :
{question}

RÉPONSE DE L'UTILISATEUR :
{user_answer}{context}

Évalue sur les 4 critères (0-10 chacun) :
1. Compréhension du concept
2. Profondeur d'analyse
3. Exemples concrets
4. Clarté de l'explication

Retourne un JSON avec les scores, le niveau estimé et un feedback constructif.
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

            analysis = json.loads(response_text)

            # Validation basique
            if not isinstance(analysis, dict) or "scores" not in analysis:
                raise ValueError("Format d'analyse invalide")

            return analysis

        except Exception as e:
            print(f"❌ Erreur analyse question ouverte: {e}")
            # Fallback en cas d'erreur
            return {
                "scores": {
                    "comprehension": 5,
                    "profondeur": 5,
                    "exemples": 5,
                    "clarte": 5
                },
                "score_global": 5.0,
                "niveau_reel_estime": 5,
                "niveau_label": "Intermédiaire",
                "feedback": "Analyse automatique indisponible. Réponse enregistrée.",
                "points_forts": [],
                "points_amelioration": [],
                "suggestions": [],
                "error": str(e)
            }

    async def analyze_multiple_open_questions(
        self,
        questions_and_answers: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyse plusieurs questions ouvertes en batch.

        Args:
            questions_and_answers: Liste de {question, user_answer, expected_answer}

        Returns:
            Dict avec analyses individuelles et synthèse globale
        """
        analyses = []

        for qa in questions_and_answers:
            analysis = await self.analyze_open_question(
                question=qa.get("question", ""),
                user_answer=qa.get("user_answer", ""),
                expected_answer=qa.get("expected_answer")
            )

            # Ajouter la question au résultat
            analysis["question"] = qa.get("question", "")
            analysis["user_answer"] = qa.get("user_answer", "")

            analyses.append(analysis)

        # Calculer la moyenne globale
        if analyses:
            avg_score = sum(a["score_global"] for a in analyses) / len(analyses)

            # Estimer le niveau global
            if avg_score <= 2.5:
                niveau_global = 2
                niveau_label_global = "Débutant"
            elif avg_score <= 4:
                niveau_global = 3
                niveau_label_global = "Débutant+"
            elif avg_score <= 5.5:
                niveau_global = 5
                niveau_label_global = "Intermédiaire bas"
            elif avg_score <= 7:
                niveau_global = 6
                niveau_label_global = "Intermédiaire"
            elif avg_score <= 8:
                niveau_global = 7
                niveau_label_global = "Intermédiaire avancé"
            elif avg_score <= 9:
                niveau_global = 8
                niveau_label_global = "Avancé"
            else:
                niveau_global = 10
                niveau_label_global = "Expert"
        else:
            avg_score = 0
            niveau_global = 1
            niveau_label_global = "Non évalué"

        # Agréger les points forts/amélioration
        all_strengths = []
        all_improvements = []
        all_suggestions = []

        for a in analyses:
            all_strengths.extend(a.get("points_forts", []))
            all_improvements.extend(a.get("points_amelioration", []))
            all_suggestions.extend(a.get("suggestions", []))

        # Dédupliquer
        all_strengths = list(set(all_strengths))
        all_improvements = list(set(all_improvements))
        all_suggestions = list(set(all_suggestions))

        return {
            "analyses_individuelles": analyses,
            "synthese_globale": {
                "score_moyen": round(avg_score, 2),
                "niveau_estime": niveau_global,
                "niveau_label": niveau_label_global,
                "nombre_questions": len(analyses),
                "points_forts_globaux": all_strengths[:5],  # Top 5
                "points_amelioration_globaux": all_improvements[:5],
                "suggestions_globales": all_suggestions[:5]
            }
        }


# Instance globale
open_question_analyzer = OpenQuestionAnalyzer()

