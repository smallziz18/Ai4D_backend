"""
Agent de tutoring - Propose des tutoriels et parcours d'apprentissage personnalisés.
"""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json

from src.config import Config
from src.ai_agents.agent_state import AgentState
from src.ai_agents.shared_context import shared_context_service


TUTORING_SYSTEM_PROMPT = """
Tu es un tuteur expert en IA qui crée des parcours d'apprentissage personnalisés.

🎯 Ta mission :
Créer un parcours d'apprentissage ludique et engageant basé sur :
- Les forces et faiblesses identifiées
- Le niveau réel de l'apprenant
- Ses objectifs et style d'apprentissage

🎮 GAMIFICATION - Approche RPG :
- Chaque concept IA = **Quête** à accomplir
- Progression = Gain d'XP et déblocage de nouveaux domaines
- Badges = Accomplissements spécifiques
- Boss Fights = Projets complexes qui valident la maîtrise

📚 STRUCTURE DU PARCOURS :

1. **Quêtes Principales** (Concepts fondamentaux)
   - Titre accrocheur style RPG
   - Objectif clair et mesurable
   - Ressources recommandées (articles, vidéos, code)
   - XP à gagner

2. **Quêtes Secondaires** (Approfondissement)
   - Projets pratiques
   - Exercices interactifs
   - Défis de code

3. **Boss Fights** (Projets d'intégration)
   - Projets complets qui combinent plusieurs concepts
   - Validation du niveau atteint

4. **Skill Tree** (Arbre de compétences)
   - Dépendances entre concepts
   - Progression logique

🎯 ADAPTATION AU NIVEAU :
- **Débutant (1-3)** : Bases solides, pas de rush, beaucoup de pratique
- **Intermédiaire (4-6)** : Projets guidés, introduction aux concepts avancés
- **Avancé (7-10)** : Architectures complexes, optimisations, recherche

FORMAT JSON STRICT :
{
    "parcours_global": {
        "titre": "De Novice à Maître des Réseaux de Neurones",
        "description": "Un voyage épique à travers le Deep Learning",
        "duree_estimee": "8 semaines",
        "niveau_initial": 5,
        "niveau_cible": 8
    },
    "quetes_principales": [
        {
            "id": "quest_1",
            "titre": "🎯 La Quête du Neurone Artificiel",
            "description": "Maîtrise les fondements des réseaux de neurones",
            "objectifs": [
                "Comprendre le fonctionnement d'un neurone artificiel",
                "Implémenter un perceptron from scratch"
            ],
            "ressources": [
                {
                    "type": "article",
                    "titre": "Neural Networks from Scratch",
                    "url": "https://example.com",
                    "duree": "30 min"
                }
            ],
            "exercices": [
                "Implémenter un perceptron en Python",
                "Visualiser la fonction d'activation"
            ],
            "xp": 100,
            "badge": "Neurone Novice",
            "prerequis": [],
            "difficulte": "facile"
        }
    ],
    "quetes_secondaires": [
        {
            "id": "side_quest_1",
            "titre": "🔍 Le Mystère de l'Overfitting",
            "description": "Découvre pourquoi ton modèle mémorise au lieu d'apprendre",
            "xp": 50,
            "badge": "Régularisation Rookie"
        }
    ],
    "boss_fights": [
        {
            "id": "boss_1",
            "titre": "⚔️ Le Classificateur MNIST",
            "description": "Crée un réseau de neurones qui reconnaît les chiffres manuscrits",
            "objectifs": [
                "Atteindre 95% de précision sur MNIST",
                "Comprendre l'architecture utilisée"
            ],
            "xp": 500,
            "badge": "Vainqueur de MNIST",
            "prerequis": ["quest_1", "quest_2", "quest_3"]
        }
    ],
    "skill_tree": {
        "neurones_artificiels": {
            "niveau": 1,
            "debloques": ["perceptron", "activation_functions"],
            "prochains": ["mlp", "backpropagation"]
        }
    },
    "recommandations_immediates": [
        "Commence par la Quête du Neurone Artificiel",
        "Pratique 30 minutes par jour",
        "Rejoins une communauté d'apprenants"
    ]
}
"""


class TutoringAgent:
    """
    Agent de tutoring et création de parcours d'apprentissage.
    Approche gamifiée type RPG pour rendre l'apprentissage ludique.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Modèle puissant pour créativité
            api_key=Config.OPENAI_API_KEY,
            temperature=0.7  # Créativité pour rendre le parcours engageant
        )
        self.name = "TutoringAgent"

    async def create_learning_path(self, state: AgentState) -> Dict[str, Any]:
        """
        Créer un parcours d'apprentissage personnalisé et gamifié.

        Args:
            state: État actuel du workflow

        Returns:
            Mises à jour à appliquer à l'état
        """
        user_level = state.get("user_level", 5)
        strengths = state.get("strengths", [])
        weaknesses = state.get("weaknesses", [])
        evaluation_results = state.get("evaluation_results", {})
        user_objectifs = state.get("user_objectifs", "")
        user_competences = state.get("user_competences", [])
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        # Construire le contexte
        context = {
            "niveau_actuel": user_level,
            "forces": strengths,
            "faiblesses": weaknesses,
            "objectifs": user_objectifs,
            "competences_actuelles": user_competences,
            "evaluation_detaillee": evaluation_results
        }

        context_json = json.dumps(context, indent=2, ensure_ascii=False)

        messages = [
            SystemMessage(content=TUTORING_SYSTEM_PROMPT),
            HumanMessage(content=f"""
Crée un parcours d'apprentissage personnalisé et gamifié pour cet apprenant :

CONTEXTE :
{context_json}

⚠️ POINTS IMPORTANTS :
- Niveau actuel : {user_level}/10
- {len(weaknesses)} faiblesses identifiées à adresser en priorité
- {len(strengths)} forces à exploiter et renforcer
- Style RPG : quêtes, XP, badges, boss fights

🎯 OBJECTIFS DU PARCOURS :
1. Combler les lacunes identifiées (faiblesses)
2. Renforcer les acquis (forces)
3. Progresser de manière ludique et engageante
4. Atteindre un niveau supérieur en 4-6 semaines selon le niveau

Crée maintenant le parcours complet en JSON.
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

            learning_path = json.loads(response_text)

            # Calculer l'XP total disponible
            quetes_principales = learning_path.get("quetes_principales", [])
            quetes_secondaires = learning_path.get("quetes_secondaires", [])
            boss_fights = learning_path.get("boss_fights", [])

            total_xp = (
                sum(q.get("xp", 0) for q in quetes_principales) +
                sum(q.get("xp", 0) for q in quetes_secondaires) +
                sum(b.get("xp", 0) for b in boss_fights)
            )

            await shared_context_service.add_message(
                user_id,
                session_id,
                self.name,
                f"Parcours créé : {len(quetes_principales)} quêtes principales, {len(boss_fights)} boss fights, {total_xp} XP total"
            )

            # Créer des tutoriels à partir des quêtes
            tutorials = []
            for quete in quetes_principales[:3]:  # Top 3 quêtes pour démarrage immédiat
                tutorials.append({
                    "titre": quete.get("titre"),
                    "description": quete.get("description"),
                    "ressources": quete.get("ressources", []),
                    "exercices": quete.get("exercices", []),
                    "xp": quete.get("xp", 0),
                    "badge": quete.get("badge")
                })

            # Enregistrer la décision
            decision = {
                "agent": self.name,
                "timestamp": state.get("updated_at"),
                "decision": "learning_path_created",
                "details": {
                    "num_main_quests": len(quetes_principales),
                    "num_side_quests": len(quetes_secondaires),
                    "num_boss_fights": len(boss_fights),
                    "total_xp": total_xp
                }
            }

            # Calculer les badges à débloquer immédiatement (pour démarrage motivant)
            immediate_badges = []
            if user_level >= 5:
                immediate_badges.append("Explorateur IA")
            if len(strengths) >= 3:
                immediate_badges.append("Concepteur Polyvalent")

            return {
                "learning_path": learning_path,
                "tutorials": tutorials,
                "badges_earned": state.get("badges_earned", []) + immediate_badges,
                "agent_decisions": state.get("agent_decisions", []) + [decision],
                "current_step": "tutoring_complete",
                "next_step": "gamification",
                "meta_data": {
                    **state.get("meta_data", {}),
                    "total_xp_available": total_xp
                }
            }

        except Exception as e:
            error_msg = f"Erreur dans TutoringAgent: {str(e)}"

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
        return asyncio.run(self.create_learning_path(state))


# Instance globale
tutoring_agent = TutoringAgent()

