#!/usr/bin/env python3
"""Script pour vérifier et déboguer le profil MongoDB"""

import asyncio
from uuid import UUID
from src.db.mongo_db import mongo_db
from src.profile.services import profile_service

async def check_mongodb():
    print("=" * 80)
    print("VÉRIFICATION MONGODB - PROFILS")
    print("=" * 80)

    # 1. Vérifier la connexion
    try:
        collections = mongo_db.list_collection_names()
        print(f"\n✅ MongoDB connecté")
        print(f"Collections disponibles: {collections}")
    except Exception as e:
        print(f"\n❌ Erreur de connexion MongoDB: {e}")
        return

    # 2. Compter les profils
    try:
        count = mongo_db.profils.count_documents({})
        print(f"\n📊 Nombre de profils: {count}")

        if count == 0:
            print("\n❌ AUCUN PROFIL dans MongoDB!")
            print("\nC'est pour ça que /recommendations retourne 404!")
            print("\nSolutions:")
            print("  1. Le profil n'a jamais été créé")
            print("  2. Vérifier que l'endpoint /api/profile/v1/me crée bien le profil")
            print("  3. Lancer le questionnaire initial pour créer le profil")
        else:
            # Afficher les profils
            profils = list(mongo_db.profils.find().limit(5))
            print(f"\n📋 Profils trouvés:")
            for i, p in enumerate(profils, 1):
                print(f"\n  {i}. Profil:")
                print(f"     - _id: {p.get('_id')}")
                print(f"     - utilisateur_id: {p.get('utilisateur_id')}")
                print(f"     - niveau: {p.get('niveau')}")
                print(f"     - xp: {p.get('xp')}")
                print(f"     - questionnaire_initial_complete: {p.get('questionnaire_initial_complete', False)}")

                recs = p.get('recommandations', [])
                print(f"     - recommandations: {len(recs)} recommandation(s)")
                if recs:
                    for j, rec in enumerate(recs[:3], 1):
                        print(f"        {j}. {rec}")

                # Vérifier l'analyse
                analyse = p.get('analyse_questions_ouvertes')
                if analyse:
                    print(f"     - analyse_questions_ouvertes: ✅ Présente")
                else:
                    print(f"     - analyse_questions_ouvertes: ❌ Absente")

    except Exception as e:
        print(f"\n❌ Erreur lors de la lecture des profils: {e}")
        import traceback
        traceback.print_exc()

    # 3. Tester la récupération via le service
    print("\n" + "=" * 80)
    print("TEST DU SERVICE PROFILE")
    print("=" * 80)

    # Utiliser l'UUID des logs
    test_user_id = "b935c266-caf0-42e3-87f6-dd1788cd0fc1"

    try:
        user_uuid = UUID(test_user_id)
        profile = await profile_service.get_profile_by_user_id(user_uuid)

        if profile:
            print(f"\n✅ Profil trouvé via service pour user {test_user_id}")
            print(f"   - Niveau: {profile.niveau}")
            print(f"   - XP: {profile.xp}")
            print(f"   - Recommandations: {len(profile.recommandations or [])} ")
            print(f"   - Questionnaire complété: {profile.questionnaire_initial_complete}")
        else:
            print(f"\n❌ Aucun profil trouvé via service pour user {test_user_id}")
            print("\n💡 Solution: Créer le profil via l'endpoint POST /api/profile/v1/")

    except Exception as e:
        print(f"\n❌ Erreur lors de la récupération du profil: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_mongodb())

