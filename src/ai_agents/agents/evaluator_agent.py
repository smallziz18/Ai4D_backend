"""
Agent d'évaluation - Évalue les réponses avec focus sur les questions ouvertes.
"""
from typing import Dict, Any  # List supprimé
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import Config
from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service


EVALUATOR_SYSTEM_PROMPT = """
Tu es un expert en évaluation des compétences IA.

🎯 Ta mission :
Évaluer les réponses avec FOCUS ABSOLU sur les questions ouvertes.

⚠️ PRINCIPE FONDAMENTAL :
**Les questions ouvertes sont LA SOURCE DE VÉRITÉ** pour évaluer le vrai niveau.

📊 MÉTHODE D'ÉVALUATION :

1. **QUESTIONS OUVERTES (POIDS 70%)** ⚠️ PRIORITÉ ABSOLUE
   Pour CHAQUE question ouverte, évalue :
   
   a) **Sens et cohérence** (0-10) :
      - La réponse montre-t-elle une vraie compréhension du concept ?
      - Les termes sont-ils utilisés correctement ?
      
   b) **Profondeur conceptuelle** (0-10) :
      - Utilise-t-elle les bons termes techniques ?
      - Explique-t-elle le "pourquoi" et pas seulement le "quoi" ?
      
   c) **Précision** (0-10) :
      - Les exemples sont-ils pertinents ?
      - Les explications sont-elles justes techniquement ?
      
   d) **Exhaustivité** (0-10) :
      - A-t-elle mentionné les éléments clés ?
      - Est-elle complète sans être superficielle ?
   
   **Scoring détaillé** :
   - Réponse vide ou hors-sujet : 0/10
   - Réponse superficielle sans termes techniques : 2/10
   - Réponse correcte mais incomplète : 5/10
   - Réponse solide avec bons concepts : 7/10
   - Réponse approfondie avec exemples et justifications : 10/10
   
   Calcule la **moyenne des questions ouvertes** (ex: 6.5/10)

2. **QCM / VRAI-FAUX (POIDS 30%)**
   - Calcule simplement le % de bonnes réponses
   - Convertis en note /10

3. **CALCUL FINAL DU NIVEAU**
   ```
   niveau_final = (moyenne_questions_ouvertes × 0.7) + (score_qcm_vf × 0.3)
   ```

4. **RÈGLES DE PLAFONNEMENT** ⚠️ IMPORTANT
   - Si moyenne questions ouvertes < 4/10 → niveau MAX = 3
   - Si moyenne questions ouvertes < 6/10 → niveau MAX = 5
   - Si réponses ouvertes vides ou incohérentes → niveau MAX = 2
   - Si moyenne questions ouvertes > 8/10 → niveau MIN = 7 (même avec QCM faibles)

5. **IDENTIFICATION DES FORCES ET FAIBLESSES**
   - Forces : Concepts bien expliqués dans les questions ouvertes
   - Faiblesses : Concepts mal expliqués ou absents

FORMAT JSON STRICT :
{
    "evaluation_globale": {
        "niveau_final": 6,
        "score_qcm_vf": 8.0,
        "moyenne_questions_ouvertes": 5.5,
        "score_total_pourcentage": 65.0
    },
    "analyse_questions_ouvertes": [
        {
            "numero": 1,
            "question": "...",
            "reponse_utilisateur": "...",
            "scores": {
                "sens_coherence": 7,
                "profondeur": 6,
                "precision": 7,
                "exhaustivite": 5
            },
            "score_moyen": 6.25,
            "commentaire": "Bonne compréhension de base mais manque de profondeur sur..."
        }
    ],
    "forces_identifiees": ["Bonne compréhension des CNN", "Maîtrise du concept de loss function"],
    "faiblesses_identifiees": ["Confusion sur la backpropagation", "Méconnaissance des architectures Transformer"],
    "recommandations": [
        "Approfondir la compréhension de la backpropagation avec des exercices pratiques",
        "Étudier l'architecture Transformer (attention mechanisms)"
    ],
    "prochaine_etape": "tutoring"
}
"""


class EvaluatorAgent:
    """
    Agent d'évaluation des réponses.
    Focus particulier sur l'analyse des questions ouvertes.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Modèle plus puissant pour l'évaluation
            api_key=Config.OPENAI_API_KEY,
            temperature=0.2  # Très faible pour objectivité
        )
        self.name = "EvaluatorAgent"

    def _deterministic_evaluation(self, questions: list, responses: list) -> Dict[str, Any]:  # changé async -> sync
        """Évaluation déterministe pour garantir l'application stricte des règles.
        Retourne un objet au format evaluation_results partiel.
        """
        import re

        # Indexer les réponses par numero
        responses_map = {r.get("numero"): r for r in responses}

        open_types = {"QuestionOuverte", "ListeOuverte"}
        qcm_types = {"ChoixMultiple", "VraiOuFaux"}

        open_scores = []
        open_analysis = []
        total_qcm = 0
        correct_qcm = 0

        for q in questions:
            numero = q.get("numero")
            q_type = q.get("type")
            user_resp_obj = responses_map.get(numero)
            user_answer = user_resp_obj.get("reponse") if user_resp_obj else None

            if q_type in open_types:
                # Score 0 si réponse absente ou vide
                if not user_answer or not str(user_answer).strip():
                    score_components = {
                        "sens_coherence": 0,
                        "profondeur": 0,
                        "precision": 0,
                        "exhaustivite": 0
                    }
                    avg_score = 0.0
                    comment = "Réponse manquante → score 0"
                else:
                    # Pour une première version déterministe sans LLM, on applique un heuristique simple
                    text = str(user_answer).strip()
                    length = len(text.split())
                    tech_terms = sum(1 for t in ["réseau", "neurone", "gradient", "perte", "loss", "backpropagation", "activation", "couche", "transformer", "attention"] if t.lower() in text.lower())
                    score_components = {
                        "sens_coherence": 5 if length >= 5 else 3,
                        "profondeur": 2 + min(5, tech_terms),
                        "precision": 3 + min(4, tech_terms // 2),
                        "exhaustivite": 2 + (2 if length > 30 else 0) + (2 if tech_terms >= 3 else 0)
                    }
                    # Clamp 0-10
                    for k, v in score_components.items():
                        score_components[k] = max(0, min(10, v))
                    avg_score = sum(score_components.values()) / 4.0
                    comment = "Heuristique appliquée (sans LLM)"
                open_scores.append(avg_score)
                open_analysis.append({
                    "numero": numero,
                    "question": q.get("question"),
                    "reponse_utilisateur": user_answer,
                    "scores": score_components,
                    "score_moyen": round(avg_score, 2),
                    "commentaire": comment
                })
            elif q_type in qcm_types:
                total_qcm += 1
                if user_answer:
                    # Extraire lettre correcte
                    corr = q.get("correction", "").strip()
                    m_corr = re.match(r"([A-D])", corr)
                    correct_letter = m_corr.group(1) if m_corr else None
                    # Extraire lettre réponse
                    m_user = re.match(r"([A-D])", str(user_answer).strip())
                    user_letter = m_user.group(1) if m_user else None
                    if correct_letter and user_letter and correct_letter == user_letter:
                        correct_qcm += 1

        # Calculs agrégés
        if open_scores:
            moyenne_open = sum(open_scores) / len(open_scores)
        else:
            moyenne_open = 0.0

        if total_qcm > 0:
            qcm_pct = correct_qcm / total_qcm * 100.0
            score_qcm_vf = (qcm_pct / 100.0) * 10.0
        else:
            qcm_pct = 0.0
            score_qcm_vf = 0.0

        niveau_base = (moyenne_open * 0.7) + (score_qcm_vf * 0.3)

        # Application des plafonnements
        answered_open = sum(1 for a in open_analysis if a.get("reponse_utilisateur") and str(a.get("reponse_utilisateur")).strip())
        if answered_open == 0:
            niveau_final = min(niveau_base, 2)
        elif moyenne_open < 4:
            niveau_final = min(niveau_base, 3)
        elif moyenne_open < 6:
            niveau_final = min(niveau_base, 5)
        elif moyenne_open > 8:
            niveau_final = max(niveau_base, 7)
        else:
            niveau_final = niveau_base

        # Normalisation et arrondi
        niveau_final = round(niveau_final, 1)

        # Label lisible
        if niveau_final <= 2:
            niveau_label = "Débutant"
        elif niveau_final <= 3:
            niveau_label = "Débutant+"
        elif niveau_final <= 5:
            niveau_label = "Intermédiaire Bas"
        elif niveau_final <= 7:
            niveau_label = "Intermédiaire"
        elif niveau_final <= 8.5:
            niveau_label = "Avancé"
        else:
            niveau_label = "Expert"

        return {
            "evaluation_globale": {
                "niveau_final": niveau_final,
                "niveau_label": niveau_label,
                "score_qcm_vf": round(score_qcm_vf, 2),
                "moyenne_questions_ouvertes": round(moyenne_open, 2),
                "score_total_pourcentage": round(((niveau_final / 10.0) * 100), 1),
                "total_qcm": total_qcm,
                "correct_qcm": correct_qcm,
                "open_questions": len(open_scores),
                "open_answered": answered_open
            },
            "analyse_questions_ouvertes": open_analysis,
            "forces_identifiees": [],
            "faiblesses_identifiees": [],
            "recommandations": self._build_recommendations(moyenne_open, score_qcm_vf, answered_open, open_analysis),
            "prochaine_etape": "tutoring"
        }

    def _build_recommendations(self, moyenne_open: float, score_qcm_vf: float, answered_open: int, open_analysis: list) -> list:
        rec = []
        if answered_open == 0:
            rec.append("Répondre aux questions ouvertes est prioritaire : elles déterminent votre niveau réel.")
            rec.append("Refaire un questionnaire en prenant le temps d'expliquer les concepts.")
        elif moyenne_open < 4:
            rec.append("Vos réponses ouvertes manquent de profondeur : travaillez la compréhension conceptuelle.")
        elif moyenne_open < 6:
            rec.append("Améliorer la précision et l'exhaustivité des explications dans les questions ouvertes.")
        if score_qcm_vf < 5:
            rec.append("Renforcer les bases via des quiz ciblés (révision des fondamentaux).")
        if moyenne_open >= 6 and score_qcm_vf >= 6:
            rec.append("Commencer des mini-projets pour consolider théorie + pratique.")
        if moyenne_open >= 8:
            rec.append("Approfondir des sujets avancés : optimisation, architectures récentes.")
        return rec

    async def evaluate(self, state: AgentState) -> Dict[str, Any]:
        """
        Évaluer les réponses de l'utilisateur.

        Args:
            state: État actuel du workflow

        Returns:
            Mises à jour à appliquer à l'état
        """
        questions = state.get("questions", [])
        responses = state.get("responses", [])
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        if not questions or not responses:
            return {"error_message": "Pas de questions ou réponses à évaluer", "needs_human_review": True}

        # Calcul déterministe initial
        deterministic = self._deterministic_evaluation(questions, responses)  # plus coroutine
        eval_globale = deterministic.get("evaluation_globale", {})
        niveau_final = eval_globale.get("niveau_final", 5)
        niveau_label = eval_globale.get("niveau_label", "Indéterminé")

        # Décider si on appelle le LLM pour enrichir (seulement si au moins une réponse ouverte non vide)
        answered_open = eval_globale.get("open_answered", 0)
        use_llm = answered_open > 0

        if not use_llm:
            # Pas d'appel LLM : retourner directement
            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                f"Évaluation déterministe: Niveau {niveau_final}/10 (aucune réponse ouverte)"
            )
            decision = {
                "agent": self.name,
                "timestamp": state.get("updated_at"),
                "decision": "evaluation_complete",
                "details": {"niveau_final": niveau_final, "deterministe": True}
            }
            return {
                "evaluation_results": deterministic,
                "open_question_analysis": {
                    "questions_analysees": deterministic.get("analyse_questions_ouvertes", []),
                    "moyenne": eval_globale.get("moyenne_questions_ouvertes", 0)
                },
                "user_level": niveau_final,
                "user_level_label": niveau_label,
                "strengths": deterministic.get("forces_identifiees", []),
                "weaknesses": deterministic.get("faiblesses_identifiees", []),
                "recommendations": deterministic.get("recommandations", []),
                "agent_decisions": state.get("agent_decisions", []) + [decision],
                "current_step": "evaluation_complete",
                "next_step": "tutoring"
            }

        # Sinon enrichissement LLM (On lui donne les scores déjà fixés et lui demandons seulement des commentaires et des forces/faiblesses sans modifier niveau_final)
        import json
        payload = {
            "questions": questions,
            "responses": responses,
            "scores_deterministes": deterministic
        }
        qa_json = json.dumps(payload, indent=2, ensure_ascii=False)
        messages = [
            SystemMessage(content=EVALUATOR_SYSTEM_PROMPT + "\nIMPORTANT: Ne modifie PAS 'niveau_final'. Ajoute uniquement forces_identifiees, faiblesses_identifiees, commentaires détaillés."),
            HumanMessage(content=f"Voici les données avec scores déjà calculés. Complète uniquement forces/faiblesses/recommandations qualitatives en JSON sans changer niveau_final:\n{qa_json}")
        ]
        try:
            llm_resp = await self.llm.ainvoke(messages)
            llm_text = llm_resp.content
            if "```json" in llm_text:
                llm_text = llm_text.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_text:
                llm_text = llm_text.split("```")[1].split("```")[0].strip()
            enriched = json.loads(llm_text)
        except Exception:
            enriched = {}

        # Fusion: conserver tout ce qui est déterministe comme source de vérité
        forces = enriched.get("forces_identifiees") or deterministic.get("forces_identifiees") or []
        faiblesses = enriched.get("faiblesses_identifiees") or deterministic.get("faiblesses_identifiees") or []
        rec_enriched = enriched.get("recommandations") or []
        # On combine recommandations sans doublons
        rec_final = list(dict.fromkeys(deterministic.get("recommandations", []) + rec_enriched))

        evaluation_results = {**deterministic}
        evaluation_results["forces_identifiees"] = forces
        evaluation_results["faiblesses_identifiees"] = faiblesses
        evaluation_results["recommandations"] = rec_final

        await shared_context_service.add_message(
            user_id,
            session_id,
            self.name,
            f"Évaluation enrichie: Niveau {niveau_final}/10 (open_avg={eval_globale.get('moyenne_questions_ouvertes', 0)}/10)"
        )
        decision = {
            "agent": self.name,
            "timestamp": state.get("updated_at"),
            "decision": "evaluation_complete",
            "details": {"niveau_final": niveau_final, "deterministe": False, "open_answered": answered_open}
        }
        return {
            "evaluation_results": evaluation_results,
            "open_question_analysis": {
                "questions_analysees": evaluation_results.get("analyse_questions_ouvertes", []),
                "moyenne": eval_globale.get("moyenne_questions_ouvertes", 0)
            },
            "user_level": niveau_final,
            "user_level_label": niveau_label,
            "strengths": forces,
            "weaknesses": faiblesses,
            "recommendations": rec_final,
            "agent_decisions": state.get("agent_decisions", []) + [decision],
            "current_step": "evaluation_complete",
            "next_step": "tutoring"
        }

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        import asyncio
        return asyncio.run(self.evaluate(state))


evaluator_agent = EvaluatorAgent()
