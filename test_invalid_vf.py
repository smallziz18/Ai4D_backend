"""
Test validation questions VraiOuFaux incomplètes ou invalides.
"""
import asyncio
from src.ai_agents.agents.question_generator_agent import question_generator_agent
from src.ai_agents.agent_state import create_initial_state

async def test_invalid_vraioufaux():
    print("🧪 Test détection questions VraiOuFaux invalides\n")

    # Simuler des questions avec différents patterns invalides
    test_cases = [
        {
            "question": "Le surapprentissage se produit lorsque :",
            "should_detect": True,
            "reason": "Question incomplète (termine par :)"
        },
        {
            "question": "Les CNN sont utilisés pour ?",
            "should_detect": True,
            "reason": "Question interrogative"
        },
        {
            "question": "Le gradient...",
            "should_detect": True,
            "reason": "Question incomplète (termine par ...)"
        },
        {
            "question": "CNN",
            "should_detect": True,
            "reason": "Question trop courte"
        },
        {
            "question": "Le sur-apprentissage se produit lorsque le modèle mémorise les données d'entraînement.",
            "should_detect": False,
            "reason": "Affirmation complète valide"
        },
        {
            "question": "Les réseaux de neurones peuvent apprendre des patterns complexes.",
            "should_detect": False,
            "reason": "Affirmation complète valide"
        }
    ]

    print("=" * 70)
    print("Tests de détection de patterns invalides\n")

    for i, case in enumerate(test_cases, 1):
        question = case["question"]
        should_detect = case["should_detect"]
        reason = case["reason"]

        print(f"Test {i}: {reason}")
        print(f"Question: \"{question}\"")

        # Détection manuelle des patterns (même logique que dans le code)
        invalid_patterns = [
            question.endswith(":"),
            question.endswith("..."),
            " est :" in question.lower() and question.endswith(":"),
            " sont :" in question.lower() and question.endswith(":"),
            question.count("?") > 0,
            len(question.split()) < 5,
        ]

        is_invalid = any(invalid_patterns)

        if should_detect:
            if is_invalid:
                print("✅ DÉTECTÉ comme invalide (attendu)")
            else:
                print("❌ NON DÉTECTÉ (devrait être invalide)")
        else:
            if is_invalid:
                print("❌ DÉTECTÉ comme invalide (devrait être valide)")
            else:
                print("✅ Reconnu comme valide (attendu)")

        print()

    print("=" * 70)
    print("\n🔬 Test avec génération réelle de questions\n")

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

    state["meta_data"] = {
        "profiler_analysis": {
            "estimated_level": 5,
            "learning_style": "balanced",
            "priority_domains": ["machine_learning", "deep_learning"]
        }
    }

    try:
        result = await question_generator_agent.generate_questions(state, num_questions=10)

        if result.get("error_message"):
            print(f"❌ Erreur: {result['error_message']}")
            return

        questions = result.get("questions", [])
        vf_questions = [q for q in questions if q.get("type") == "VraiOuFaux"]

        print(f"✅ {len(questions)} questions générées")
        print(f"📊 Questions VraiOuFaux: {len(vf_questions)}\n")

        all_valid = True
        for i, q in enumerate(vf_questions, 1):
            question_text = q.get("question")
            print(f"--- VraiOuFaux #{i} ---")
            print(f"Question: {question_text}")

            # Vérifier qu'elle ne termine pas par : ou ...
            if question_text.endswith(":") or question_text.endswith("..."):
                print("❌ INVALIDE: Question incomplète détectée !")
                all_valid = False
            elif "?" in question_text:
                print("❌ INVALIDE: Question interrogative détectée !")
                all_valid = False
            elif len(question_text.split()) < 5:
                print("❌ INVALIDE: Question trop courte !")
                all_valid = False
            else:
                print("✅ Affirmation complète valide")

            print()

        print("=" * 70)
        if all_valid and vf_questions:
            print("✅ TOUTES LES QUESTIONS VRAIOUFAUX SONT VALIDES")
        elif not vf_questions:
            print("⚠️ Aucune question VraiOuFaux générée")
        else:
            print("❌ CERTAINES QUESTIONS VRAIOUFAUX SONT INVALIDES")

    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_invalid_vraioufaux())

