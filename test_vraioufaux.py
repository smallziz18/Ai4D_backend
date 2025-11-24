"""
Test rapide pour valider la génération de questions VraiOuFaux.
"""
import asyncio
import json
from src.ai_agents.agents.question_generator_agent import question_generator_agent
from src.ai_agents.agent_state import create_initial_state

async def test_vraioufaux_generation():
    print("🧪 Test génération questions VraiOuFaux\n")

    # Créer un état de test
    state = create_initial_state(
        user_id="test_user",
        session_id="test_session",
        user_profile={
            "niveau_technique": 5,
            "competences": ["machine_learning"],
            "objectifs_apprentissage": "Maîtriser les bases du ML"
        }
    )

    # Ajouter métadonnées du profiler
    state["meta_data"] = {
        "profiler_analysis": {
            "estimated_level": 5,
            "learning_style": "balanced",
            "priority_domains": ["machine_learning", "deep_learning"]
        }
    }

    print("Génération de 10 questions...\n")

    try:
        result = await question_generator_agent.generate_questions(state, num_questions=10)

        if result.get("error_message"):
            print(f"❌ Erreur: {result['error_message']}")
            return

        questions = result.get("questions", [])
        print(f"✅ {len(questions)} questions générées\n")

        # Analyser les questions VraiOuFaux
        vf_questions = [q for q in questions if q.get("type") == "VraiOuFaux"]

        print(f"📊 Questions VraiOuFaux: {len(vf_questions)}\n")

        all_valid = True
        for i, q in enumerate(vf_questions, 1):
            print(f"--- Question VraiOuFaux #{i} ---")
            print(f"Question: {q.get('question')}")
            print(f"Options: {q.get('options')}")
            print(f"Correction: {q.get('correction')}")

            # Validation
            options = q.get("options", [])
            expected_options = ["A. Vrai", "B. Faux"]

            if options == expected_options:
                print("✅ Format correct")
            else:
                print(f"❌ Format incorrect ! Attendu: {expected_options}, Reçu: {options}")
                all_valid = False

            correction = q.get("correction", "")
            if correction.startswith("A") or correction.startswith("B"):
                print("✅ Correction commence par A ou B")
            else:
                print(f"⚠️ Correction ne commence pas par A/B: {correction}")
                all_valid = False

            print()

        # Vérifier la diversité des réponses (éviter biais)
        if vf_questions:
            a_count = sum(1 for q in vf_questions if q.get("correction", "").startswith("A"))
            b_count = sum(1 for q in vf_questions if q.get("correction", "").startswith("B"))
            print(f"📈 Répartition réponses: A={a_count}, B={b_count}")

            if a_count == 0 or b_count == 0:
                print("⚠️ Toutes les réponses sont identiques (biais détecté)")
            else:
                print("✅ Réponses variées (pas de biais systématique)")

        print("\n" + "="*50)
        if all_valid:
            print("✅ TOUS LES TESTS PASSÉS")
        else:
            print("❌ CERTAINS TESTS ONT ÉCHOUÉ")

    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vraioufaux_generation())

