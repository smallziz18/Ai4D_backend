

#!/usr/bin/env python3
"""Script pour créer un profil de test"""

import asyncio
from uuid import UUID
from src.profile.services import profile_service
from src.profile.schema import ProfilCreate

async def create_test_profile():
    # UUID de l'utilisateur qui a fait le dernier test
    user_id = "07ebf7e5-2453-4801-a584-9eabbe1bb939"

    print(f"Création du profil pour l'utilisateur {user_id}...")
    print(f"Email: smzdiouf@gmail.com")

    try:
        user_uuid = UUID(user_id)

        # Vérifier si le profil existe déjà
        existing = await profile_service.get_profile_by_user_id(user_uuid)
        if existing:
            print(f"✅ Le profil existe déjà!")
            print(f"   - Niveau: {existing.niveau}")
            print(f"   - XP: {existing.xp}")
            return

        # Créer le profil
        profile_data = ProfilCreate(
            utilisateur_id=user_uuid,
            niveau=1,
            xp=0,
            badges=[],
            competences=[],
            energie=5
        )

        profile = await profile_service.create_profile(profile_data)
        print(f"✅ Profil créé avec succès!")
        print(f"   - ID MongoDB: {profile.id}")
        print(f"   - Niveau: {profile.niveau}")
        print(f"   - XP: {profile.xp}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_test_profile())

