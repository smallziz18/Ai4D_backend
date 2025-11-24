"""
Script de test pour le nouveau système LangGraph Multi-Agents V2.

Usage:
    python test_langgraph_system.py
"""
import asyncio
import sys
from datetime import datetime

# Test imports
try:
    from src.ai_agents.workflow import generate_profile_questions, analyze_and_create_profile
    from src.ai_agents.agent_state import create_initial_state
    from src.ai_agents.shared_context import shared_context_service
    print("✅ Imports réussis")
except Exception as e:
    print(f"❌ Erreur d'import : {e}")
    sys.exit(1)


async def test_workflow():
    """Test complet du workflow LangGraph"""

    print("\n" + "="*60)
    print("🧪 TEST DU SYSTÈME LANGGRAPH MULTI-AGENTS V2")
    print("="*60 + "\n")

    # === Test 1 : Génération de questions ===
    print("📝 Test 1 : Génération de questions")
    print("-" * 40)

    test_user_profile = {
        "id": "test-user-123",
        "nom": "Test",
        "prenom": "User",
        "username": "testuser",
        "email": "test@example.com",
        "status": "Etudiant",
        "niveau_technique": 5,
        "competences": ["Python", "Machine Learning"],
        "objectifs_apprentissage": "Maîtriser le Deep Learning",
        "motivation": "Changer de carrière",
        "niveau_energie": 7
    }

    try:
        result = await generate_profile_questions(
            user_id="test-user-123",
            user_profile=test_user_profile
        )

        print(f"✅ Questions générées avec succès")
        print(f"   - Session ID: {result['session_id']}")
        print(f"   - Nombre de questions: {len(result.get('questions', []))}")
        print(f"   - Niveau estimé: {result.get('user_level')}/10")

        # Analyser les types de questions
        questions = result.get('questions', [])
        types_count = {}
        for q in questions:
            qtype = q.get('type', 'Unknown')
            types_count[qtype] = types_count.get(qtype, 0) + 1

        print(f"   - Types de questions:")
        for qtype, count in types_count.items():
            emoji = "⚠️" if qtype in ["QuestionOuverte", "ListeOuverte"] else "📋"
            print(f"     {emoji} {qtype}: {count}")

        open_questions = types_count.get("QuestionOuverte", 0) + types_count.get("ListeOuverte", 0)
        open_percentage = (open_questions / len(questions) * 100) if questions else 0

        if open_percentage >= 30:
            print(f"   ✅ Taux de questions ouvertes: {open_percentage:.1f}% (>= 30%)")
        else:
            print(f"   ⚠️ Taux de questions ouvertes: {open_percentage:.1f}% (< 30%)")

        session_id = result['session_id']

    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()
        return

    # === Test 2 : Création de réponses factices ===
    print("\n📝 Test 2 : Création de réponses factices")
    print("-" * 40)

    test_responses = []
    for q in questions:
        response = {
            "numero": q.get("numero"),
            "type": q.get("type")
        }

        if q.get("type") == "ChoixMultiple":
            response["reponse"] = "A"
        elif q.get("type") == "VraiOuFaux":
            response["reponse"] = "A"
        elif q.get("type") == "QuestionOuverte":
            response["reponse"] = "La backpropagation est un algorithme qui propage l'erreur en arrière à travers les couches du réseau de neurones, en utilisant la règle de dérivation en chaîne pour calculer les gradients."
        elif q.get("type") == "ListeOuverte":
            response["reponse"] = "CNN, RNN, LSTM"

        test_responses.append(response)

    print(f"✅ {len(test_responses)} réponses factices créées")

    # === Test 3 : Analyse des réponses ===
    print("\n📝 Test 3 : Analyse des réponses (Multi-Agents)")
    print("-" * 40)
    print("   🤖 EvaluatorAgent → Évalue les réponses")
    print("   🎓 TutoringAgent → Crée le parcours RPG")

    try:
        result = await analyze_and_create_profile(
            user_id="test-user-123",
            session_id=session_id,
            responses=test_responses
        )

        print(f"\n✅ Analyse terminée avec succès")
        print(f"\n📊 RÉSULTATS DE L'ÉVALUATION:")
        print(f"   - Niveau final: {result.get('user_level')}/10")

        eval_results = result.get('evaluation_results', {})
        eval_globale = eval_results.get('evaluation_globale', {})

        print(f"   - Score QCM/VF: {eval_globale.get('score_qcm_vf', 0):.1f}/10")
        print(f"   - Moyenne questions ouvertes: {eval_globale.get('moyenne_questions_ouvertes', 0):.1f}/10")

        forces = result.get('strengths', [])
        faiblesses = result.get('weaknesses', [])

        print(f"\n💪 FORCES IDENTIFIÉES ({len(forces)}):")
        for force in forces[:3]:
            print(f"   ✓ {force}")

        print(f"\n⚠️ FAIBLESSES IDENTIFIÉES ({len(faiblesses)}):")
        for faiblesse in faiblesses[:3]:
            print(f"   ✗ {faiblesse}")

        # Parcours d'apprentissage
        learning_path = result.get('learning_path', {})
        quetes = learning_path.get('quetes_principales', [])
        boss_fights = learning_path.get('boss_fights', [])

        print(f"\n🎮 PARCOURS D'APPRENTISSAGE RPG:")
        print(f"   - Quêtes principales: {len(quetes)}")
        print(f"   - Boss Fights: {len(boss_fights)}")

        if quetes:
            print(f"\n   Première quête:")
            print(f"   {quetes[0].get('titre', 'Sans titre')}")
            print(f"   XP: {quetes[0].get('xp', 0)} | Badge: {quetes[0].get('badge', 'Aucun')}")

        badges = result.get('badges_earned', [])
        print(f"\n🏆 BADGES DÉBLOQUÉS ({len(badges)}):")
        for badge in badges:
            print(f"   🎖️ {badge}")

        recommendations = result.get('recommendations', [])
        print(f"\n💡 RECOMMANDATIONS ({len(recommendations)}):")
        for rec in recommendations[:3]:
            print(f"   → {rec}")

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        import traceback
        traceback.print_exc()
        return

    # === Test 4 : Contexte partagé ===
    print("\n📝 Test 4 : Vérification du contexte partagé")
    print("-" * 40)

    try:
        context = await shared_context_service.get_context(
            user_id="test-user-123",
            session_id=session_id
        )

        if context:
            print(f"✅ Contexte récupéré depuis PostgreSQL/Redis")
            print(f"   - État actuel: {context.get('current_state')}")
            print(f"   - Interactions totales: {context.get('total_interactions')}")
            print(f"   - Messages dans l'historique: {len(context.get('conversation_history', []))}")

            # Afficher les 3 derniers messages
            conv_history = context.get('conversation_history', [])
            if conv_history:
                print(f"\n   Derniers messages:")
                for msg in conv_history[-3:]:
                    print(f"   [{msg.get('agent')}] {msg.get('message')[:60]}...")
        else:
            print(f"⚠️ Aucun contexte trouvé")

    except Exception as e:
        print(f"❌ Erreur lors de la récupération du contexte: {e}")
        import traceback
        traceback.print_exc()

    # === Résumé final ===
    print("\n" + "="*60)
    print("✅ TESTS TERMINÉS")
    print("="*60)
    print(f"\n🎯 Le système LangGraph Multi-Agents V2 est opérationnel !")
    print(f"\n📚 Documentation:")
    print(f"   - Architecture: ARCHITECTURE_MULTI_AGENTS.md")
    print(f"   - Migration: MIGRATION_LANGGRAPH.md")
    print(f"\n🚀 Endpoints disponibles:")
    print(f"   - POST /api/profile/v2/generate-questions")
    print(f"   - POST /api/profile/v2/submit-responses")
    print(f"   - GET  /api/profile/v2/learning-path")
    print(f"   - GET  /api/profile/v2/workflow-state/{{session_id}}")


if __name__ == "__main__":
    print("🚀 Démarrage des tests...")

    # Vérifier que les dépendances sont installées
    try:
        import langgraph
        import langchain_openai
        print("✅ Dépendances LangGraph installées")
    except ImportError as e:
        print(f"❌ Dépendances manquantes: {e}")
        print("   Exécutez: pip install langgraph langchain langchain-openai")
        sys.exit(1)

    # Vérifier la config
    try:
        from src.config import Config
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        print("✅ Configuration OpenAI OK")
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        sys.exit(1)

    # Lancer les tests
    asyncio.run(test_workflow())

