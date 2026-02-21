"""
Script de diagnostic et correction du cloisonnement multi-utilisateurs.
Vérifie que chaque utilisateur a bien son propre profil dans MongoDB.
"""

import asyncio
from motor.motor_asyncio import AsyncMotorClient
from src.config import Config

async def diagnose_user_isolation():
    """Diagnostic du cloisonnement utilisateur"""

    print("\n" + "="*60)
    print("DIAGNOSTIC DU CLOISONNEMENT MULTI-UTILISATEURS")
    print("="*60 + "\n")

    # Connexion MongoDB
    client = AsyncMotorClient(Config.MONGODB_URL)
    db = client[Config.MONGODB_DB_NAME]
    profiles_collection = db["profil"]

    try:
        # Compter les profils
        total_profiles = await profiles_collection.count_documents({})
        print(f"📊 Total de profils dans MongoDB: {total_profiles}")

        if total_profiles == 0:
            print("⚠️  Aucun profil trouvé!")
            return

        # Lister tous les profils avec leur utilisateur_id
        print("\n📋 Profils existants:\n")

        profiles = await profiles_collection.find({}, {"utilisateur_id": 1, "_id": 1}).to_list(None)

        user_ids = {}
        for profile in profiles:
            user_id = str(profile.get("utilisateur_id", "UNKNOWN"))
            profile_id = str(profile.get("_id", "UNKNOWN"))

            if user_id not in user_ids:
                user_ids[user_id] = []
            user_ids[user_id].append(profile_id)

            print(f"  • Profil: {profile_id[:12]}... | Utilisateur: {user_id[:12]}...")

        # Analyser les résultats
        print(f"\n🔍 ANALYSE:\n")
        print(f"  • Nombre d'utilisateurs uniques: {len(user_ids)}")

        # Vérifier les doublons
        duplicates = {uid: pids for uid, pids in user_ids.items() if len(pids) > 1}

        if duplicates:
            print(f"\n❌ PROBLÈME DÉTECTÉ: {len(duplicates)} utilisateur(s) ont plusieurs profils!")
            for uid, pids in duplicates.items():
                print(f"\n  Utilisateur {uid[:12]}... a {len(pids)} profils:")
                for pid in pids:
                    print(f"    - {pid}")
        else:
            print(f"\n✅ GOOD: Chaque utilisateur a UN SEUL profil")

        # Vérifier si les profils sont distincts
        print(f"\n📊 Distribution des profils par utilisateur:")
        for user_id, profile_ids in sorted(user_ids.items()):
            print(f"  • {user_id[:12]}...: {len(profile_ids)} profil(s)")

        # Recommandations
        print("\n" + "="*60)
        print("RECOMMANDATIONS")
        print("="*60)

        if duplicates:
            print("\n⚠️  DUPLICATION DÉTECTÉE!")
            print("\nPour corriger:")
            print("  1. Identifier les profils en double")
            print("  2. Garder le plus récent (par created_at)")
            print("  3. Supprimer les anciens")
            print("  4. Vérifier que chaque user_id a exactement 1 profil")
        else:
            print("\n✅ Pas de problème de cloisonnement détecté!")
            print("   Chaque utilisateur a son propre profil.")

    finally:
        client.close()
        print("\n" + "="*60 + "\n")

async def fix_user_isolation():
    """Corrige les doublons de profils"""

    print("\n" + "="*60)
    print("CORRECTION DES DOUBLONS DE PROFILS")
    print("="*60 + "\n")

    client = AsyncMotorClient(Config.MONGODB_URL)
    db = client[Config.MONGODB_DB_NAME]
    profiles_collection = db["profil"]

    try:
        # Trouver les utilisateurs avec plusieurs profils
        pipeline = [
            {"$group": {
                "_id": "$utilisateur_id",
                "count": {"$sum": 1},
                "profiles": {"$push": "$$ROOT"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]

        duplicates = await profiles_collection.aggregate(pipeline).to_list(None)

        if not duplicates:
            print("✅ Aucun doublon trouvé!")
            return

        print(f"🔍 Trouvé {len(duplicates)} utilisateur(s) avec des doublons\n")

        for dup in duplicates:
            user_id = dup["_id"]
            profiles = sorted(dup["profiles"], key=lambda p: p.get("created_at", ""), reverse=True)

            print(f"Utilisateur: {user_id}")
            print(f"  Profils à traiter: {len(profiles)}")

            # Garder le plus récent, supprimer les autres
            to_keep = profiles[0]
            to_delete = profiles[1:]

            print(f"  ✅ À conserver: {str(to_keep['_id'])[:12]}...")
            for profile in to_delete:
                profile_id = profile["_id"]
                result = await profiles_collection.delete_one({"_id": profile_id})
                print(f"  ❌ Supprimé: {str(profile_id)[:12]}... ({result.deleted_count} doc)")

        print("\n✅ Correction terminée!")

    finally:
        client.close()
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        asyncio.run(fix_user_isolation())
    else:
        asyncio.run(diagnose_user_isolation())
        print("\n💡 TIP: Pour corriger les doublons, exécutez:")
        print("   python src/ai_agents/profiler/diagnose_isolation.py fix\n")

