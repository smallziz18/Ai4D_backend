#!/usr/bin/env python3
"""
Script de test pour vérifier la sauvegarde du questionnaire initial dans MongoDB
"""
import json
import asyncio
from uuid import UUID
from datetime import datetime
from src.profile.services import profile_service
from src.db.mongo_db import mongo_db

async def test_questionnaire_initial():
    """Test complet du questionnaire initial"""

    print("=" * 80)
    print("TEST DU QUESTIONNAIRE INITIAL")
    print("=" * 80)

    # Simuler un utilisateur de test
    test_user_id = "b935c266-caf0-42e3-87f6-dd1788cd0fc1"  # Remplacer par un vrai UUID

    print(f"\n1. Vérification du profil existant pour l'utilisateur {test_user_id}")
    try:
        user_uuid = UUID(test_user_id)
    except:
        print(f"❌ UUID invalide : {test_user_id}")
        return

    profile = await profile_service.get_profile_by_user_id(user_uuid)

    if not profile:
        print(f"⚠️ Profil non trouvé. Création d'un nouveau profil...")
        from src.profile.schema import ProfilCreate
        profile_data = ProfilCreate(
            utilisateur_id=user_uuid,
            niveau=1,
            xp=0,
            badges=[],
            competences=[],
            energie=5
        )
        profile = await profile_service.create_profile(profile_data)
        print(f"✅ Profil créé : {profile.id}")
    else:
        print(f"✅ Profil trouvé : {profile.id}")
        print(f"   - Niveau : {profile.niveau}")
        print(f"   - XP : {profile.xp}")
        print(f"   - Questionnaire initial complété : {profile.questionnaire_initial_complete}")

    # Données de test du questionnaire
    questionnaire_data = {
        "questions_data": [
            {
                "question": "Expliquez le concept de backpropagation dans les réseaux de neurones",
                "type": "ouverte",
                "user_answer": "La backpropagation est un algorithme qui utilise la règle de la chaîne pour calculer les gradients de la fonction de perte par rapport aux poids du réseau. Elle propage l'erreur de la sortie vers l'entrée, permettant d'ajuster les poids par descente de gradient.",
                "correction": "Excellente réponse démontrant une compréhension approfondie",
                "is_correct": True
            },
            {
                "question": "Citez 3 types de réseaux de neurones",
                "type": "liste_ouverte",
                "user_answer": "CNN (Convolutional Neural Networks) pour le traitement d'images, RNN (Recurrent Neural Networks) pour les séquences, et Transformers pour le NLP moderne",
                "correction": "Réponse complète et précise",
                "is_correct": True
            },
            {
                "question": "Les CNN sont utilisés principalement pour :",
                "type": "qcm",
                "user_answer": "A",
                "correction": "A - Le traitement d'images",
                "is_correct": True
            },
            {
                "question": "Le Deep Learning nécessite toujours beaucoup de données",
                "type": "vraifaux",
                "user_answer": "Faux",
                "correction": "Faux - Le transfer learning permet d'utiliser moins de données",
                "is_correct": True
            }
        ],
        "score": 100
    }

    # Simuler une analyse LLM
    analyse_llm = {
        "niveau": 8,
        "niveau_reel": "avancé",
        "score_questions_ouvertes": 8.5,
        "score_qcm": 10.0,
        "comprehension_profonde": "excellente",
        "capacite_explication": "excellente",
        "competences": ["Deep Learning", "Backpropagation", "CNN", "RNN", "Transformers"],
        "objectifs": "Approfondir les architectures Transformer et explorer le reinforcement learning avancé",
        "motivation": "Forte motivation démontrée par la qualité des explications",
        "energie": 9,
        "preferences": {
            "themes": ["Deep Learning", "Computer Vision", "NLP"],
            "style_apprentissage": "mixte",
            "domaines_a_renforcer": ["Reinforcement Learning"],
            "points_forts": ["Théorie des réseaux de neurones", "Architectures modernes"]
        },
        "recommandations": [
            "🚀 Excellent niveau ! Prêt pour des concepts avancés",
            "📚 Approfondis les architectures Transformer (Attention mechanisms)",
            "💪 Pratique avec des projets de NLP modernes (BERT, GPT)",
            "🎯 Explore le Reinforcement Learning (DQN, PPO)",
            "🔍 Optimise tes modèles (pruning, quantization)"
        ],
        "commentaires": "L'utilisateur démontre une excellente compréhension des concepts fondamentaux du Deep Learning. Les réponses ouvertes sont détaillées et précises, utilisant le vocabulaire technique approprié. Niveau estimé : Avancé (8/10)."
    }

    print("\n2. Test de la sauvegarde du questionnaire initial")

    if profile.questionnaire_initial_complete:
        print("⚠️ Le questionnaire initial a déjà été complété pour cet utilisateur")
        print("   Pour tester, vous devez soit :")
        print("   a) Utiliser un autre utilisateur")
        print("   b) Réinitialiser le champ questionnaire_initial_complete à false dans MongoDB")

        # Option de réinitialisation
        print("\nVoulez-vous réinitialiser pour tester ? (Les données seront écrasées)")
        response = input("Tapez 'oui' pour continuer : ")
        if response.lower() != 'oui':
            print("❌ Test annulé")
            return

        # Réinitialiser
        mongo_db.profils.update_one(
            {"utilisateur_id": str(user_uuid)},
            {"$set": {"questionnaire_initial_complete": False}}
        )
        print("✅ Profil réinitialisé pour le test")

    try:
        print("\n3. Sauvegarde du questionnaire initial avec analyse LLM...")
        updated_profile = await profile_service.save_initial_questionnaire(
            user_uuid,
            questionnaire_data,
            analyse_llm=analyse_llm
        )

        print("✅ Questionnaire initial sauvegardé avec succès !")
        print(f"\n📊 Résultats de la sauvegarde :")
        print(f"   - Questionnaire complété : {updated_profile.questionnaire_initial_complete}")
        print(f"   - Date de complétion : {updated_profile.questionnaire_initial_date}")
        print(f"   - Nombre de réponses : {len(updated_profile.questionnaire_reponses)}")
        print(f"   - Compétences identifiées : {len(updated_profile.competences)}")
        print(f"   - Recommandations : {len(updated_profile.recommandations or [])}")

        print(f"\n🎯 Profil mis à jour :")
        print(f"   - Niveau : {updated_profile.niveau}")
        print(f"   - Énergie : {updated_profile.energie}")
        print(f"   - Objectifs : {updated_profile.objectifs[:100]}..." if updated_profile.objectifs else "   - Objectifs : Non définis")
        print(f"   - Motivation : {updated_profile.motivation[:100]}..." if updated_profile.motivation else "   - Motivation : Non définie")

        if updated_profile.competences:
            print(f"\n💪 Compétences détectées :")
            for comp in updated_profile.competences:
                print(f"   - {comp}")

        if updated_profile.recommandations:
            print(f"\n✨ Recommandations personnalisées :")
            for i, rec in enumerate(updated_profile.recommandations[:5], 1):
                print(f"   {i}. {rec}")

        if updated_profile.analyse_questions_ouvertes:
            print(f"\n🧠 Analyse des questions ouvertes :")
            analyse = updated_profile.analyse_questions_ouvertes
            print(f"   - Nombre de questions ouvertes : {analyse.get('nombre_questions_ouvertes', 0)}")

            eval_det = analyse.get('evaluation_detaillee', {})
            print(f"   - Niveau réel estimé : {eval_det.get('niveau_reel_estime', 'non déterminé')}")
            print(f"   - Compréhension profonde : {eval_det.get('comprehension_profonde', 'non évaluée')}")
            print(f"   - Capacité d'explication : {eval_det.get('capacite_explication', 'non évaluée')}")

        print("\n✅ TEST RÉUSSI - Le profil et les recommandations sont sauvegardés dans MongoDB")

    except ValueError as e:
        print(f"❌ Erreur : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()

    print("\n4. Vérification des endpoints")
    print("   Pour vérifier que les endpoints fonctionnent :")
    print(f"   - GET /api/profile/v1/me → Devrait retourner 200 avec le profil")
    print(f"   - GET /api/profile/v1/recommendations → Devrait retourner 200 avec les recommandations")

    print("\n" + "=" * 80)
    print("FIN DU TEST")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🧪 Script de Test - Questionnaire Initial\n")
    asyncio.run(test_questionnaire_initial())

