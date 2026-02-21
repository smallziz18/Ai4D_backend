from fastapi import FastAPI
from src.users.router import user_router
from src.profile.router import router
from src.profile.roadmap_router import roadmap_router
from src.profile.roadmap_test_router import router as roadmap_test_router
from .error import *
from .middelware import register_middlewares
from src.ai_agents.router import ai_router
from src.ai_agents.router_realtime import realtime_router

version = "v1"
app = FastAPI(
    version=version,
    title="Backend du projet AI4D",
    description="Plateforme d'apprentissage IA scalable avec agents multi-tâches",
)

# Register all custom exception handlers
register_error_handler(app)
register_middlewares(app)

# CORRIGER LE PRÉFIXE - Ajouter /api
app.include_router(user_router, prefix=f"/api/auth/{version}", tags=["users"])
app.include_router(router, prefix=f"/api/profile/{version}", tags=["profile"])
app.include_router(roadmap_router, prefix=f"/api/profile/{version}", tags=["Roadmap"])
app.include_router(roadmap_test_router, tags=["Roadmap Test"])  # Router de test pour Postman
app.include_router(ai_router, prefix=f"/api/ai/{version}", tags=["AI Agents"])
app.include_router(realtime_router, tags=["AI Realtime"])  # WebSocket - pas de version dans prefix


@app.get("/")
async def root():
    return {"message": "Backend AI4D API", "version": version}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": version}

