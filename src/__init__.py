from fastapi import FastAPI
from src.users.router import user_router
from src.profile.router import router
from .error import *
from .middelware import register_middlewares
from src.ai_agents.shared_context import shared_context_service
from fastapi import APIRouter, Depends
from src.users.dependencies import get_current_user
from src.users.models import Utilisateur
from src.ai_agents.router import router_ai

version = "v1"
app = FastAPI(
    version=version,
    title="Backend du projet AI4D",
    description="A faire",
)

# Register all custom exception handlers
register_error_handler(app)
register_middlewares(app)

# CORRIGER LE PRÉFIXE - Ajouter /api
app.include_router(user_router, prefix=f"/api/auth/{version}", tags=["users"])
app.include_router(router, prefix=f"/api/profile/{version}", tags=["profile"])
app.include_router(router_ai, prefix=f"/api/{version}")
