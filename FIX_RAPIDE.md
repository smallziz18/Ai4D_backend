# ⚡ FIX RAPIDE - 30 secondes

## Problème
```
TypeError: profile_analysis_task() takes 2 positional arguments but 3 were given
→ Profil NON sauvegardé dans MongoDB
→ /recommendations retourne 404
```

## Solution

```bash
# 1 seule commande
./fix_profil.sh
```

OU manuellement :

```bash
pkill -9 -f "celery worker"
python3 create_test_profile.py
celery -A src.celery_tasks worker --loglevel=info
```

## Vérification

```bash
python3 check_mongodb_profils.py
# Devrait montrer 1 profil au minimum
```

---

**📚 Docs complètes :** `CORRECTION_IMMEDIATE.md` ou `SOLUTION_URGENTE_CELERY.md`

