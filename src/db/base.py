"""
Fichier de base pour Alembic.
Importe tous les modèles SQLModel pour qu'Alembic puisse détecter les changements.
"""
from sqlmodel import SQLModel

# Importer tous les modèles pour qu'Alembic puisse les détecter
from src.users.models import Utilisateur, Professeur, Etudiant, StatutUtilisateur, Domaine
from src.users.tokens import VerificationToken
from src.ai_agents.models import AgentContext

# SQLModel utilise sa propre Base, on l'exporte pour Alembic
Base = SQLModel

# Pour Alembic
__all__ = ["Base", "Utilisateur", "Professeur", "Etudiant", "VerificationToken", "AgentContext"]

