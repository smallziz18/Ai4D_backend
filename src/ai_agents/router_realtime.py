"""
Routes WebSocket pour communication temps réel avec les agents IA.
Architecture scalable avec streaming via Redis Pub/Sub.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Optional
import json
from datetime import datetime, UTC

from src.users.dependencies import get_current_user
from src.users.models import Utilisateur as User
from src.celery_tasks import app as celery_app
from src.db.redis import r as redis_client


realtime_router = APIRouter(prefix="/api/ai/v1/realtime", tags=["AI Realtime"])


class ConnectionManager:
    """Gestionnaire de connexions WebSocket"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accepter une nouvelle connexion WebSocket"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ WebSocket connecté pour user {user_id}")

    def disconnect(self, user_id: str):
        """Déconnecter un utilisateur"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"🔌 WebSocket déconnecté pour user {user_id}")

    async def send_message(self, user_id: str, message: dict):
        """Envoyer un message à un utilisateur spécifique"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                print(f"❌ Erreur envoi message WebSocket: {e}")
                self.disconnect(user_id)

    def is_connected(self, user_id: str) -> bool:
        """Vérifier si un utilisateur est connecté"""
        return user_id in self.active_connections


manager = ConnectionManager()


@realtime_router.websocket("/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """
    WebSocket pour chat en temps réel avec streaming.

    Flux:
    1. Client se connecte via WebSocket
    2. Client envoie {"message": "...", "session_id": "..."}
    3. Backend démarre une tâche Celery
    4. Celery publie les chunks de réponse sur Redis
    5. Backend écoute Redis et stream vers le client
    6. Client reçoit la réponse en temps réel

    Args:
        websocket: Connexion WebSocket
        user_id: ID de l'utilisateur (UUID)
    """
    await manager.connect(user_id, websocket)

    try:
        while True:
            # Recevoir le message du client
            data = await websocket.receive_json()
            message = data.get("message")
            session_id = data.get("session_id", f"ws_{user_id}_{datetime.now(UTC).timestamp()}")

            if not message:
                await websocket.send_json({
                    "type": "error",
                    "error": "Message vide",
                    "timestamp": datetime.now(UTC).isoformat()
                })
                continue

            # Démarrer la tâche Celery de streaming
            task = celery_app.send_task(
                'chatbot_streaming_task',
                args=[user_id, session_id, message]
            )

            # Envoyer confirmation au client
            await websocket.send_json({
                "type": "task_started",
                "task_id": task.id,
                "status": "processing",
                "timestamp": datetime.now(UTC).isoformat()
            })

            # Écouter Redis pour les updates en streaming
            pubsub = redis_client.pubsub()
            channel = f"chatbot_stream:{task.id}"

            try:
                await pubsub.subscribe(channel)

                # Écouter les messages Redis
                async for redis_message in pubsub.listen():
                    if redis_message["type"] == "message":
                        try:
                            chunk_data = json.loads(redis_message["data"])

                            # Envoyer le chunk au client via WebSocket
                            await websocket.send_json(chunk_data)

                            # Si c'est le dernier chunk, arrêter l'écoute
                            if chunk_data.get("type") in ["complete", "error"]:
                                break

                        except json.JSONDecodeError as e:
                            print(f"❌ Erreur parsing JSON Redis: {e}")
                            continue

            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()

    except WebSocketDisconnect:
        print(f"🔌 Client {user_id} déconnecté")
        manager.disconnect(user_id)

    except Exception as e:
        print(f"❌ Erreur WebSocket pour user {user_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            })
        except:
            pass
        manager.disconnect(user_id)


@realtime_router.post("/chat/start")
async def start_chat_async(
    message: str,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Démarre une conversation asynchrone (sans WebSocket).

    Le client peut ensuite:
    1. Poller /api/ai/v1/agents/status/{task_id} pour le statut
    2. Se connecter via WebSocket pour recevoir le streaming

    Args:
        message: Message de l'utilisateur
        session_id: ID de session (optionnel)
        current_user: Utilisateur authentifié

    Returns:
        Dict avec task_id et URLs de polling
    """
    if not message or not message.strip():
        raise HTTPException(
            status_code=400,
            detail="Le message ne peut pas être vide"
        )

    # Générer un session_id si non fourni
    if not session_id:
        session_id = f"async_{current_user.id}_{datetime.now(UTC).timestamp()}"

    # Démarrer la tâche Celery
    task = celery_app.send_task(
        'chatbot_streaming_task',
        args=[str(current_user.id), session_id, message]
    )

    return {
        "task_id": task.id,
        "status": "processing",
        "session_id": session_id,
        "estimated_time_seconds": 5,
        "poll_url": f"/api/ai/v1/agents/status/{task.id}",
        "websocket_url": f"ws://127.0.0.1:8000/api/ai/v1/realtime/chat/{current_user.id}",
        "message": "Tâche démarrée. Utilisez poll_url pour vérifier le statut ou connectez-vous via WebSocket."
    }


@realtime_router.get("/connections")
async def get_active_connections(
    current_user: User = Depends(get_current_user)
):
    """
    Récupère le nombre de connexions WebSocket actives.
    (Admin only - à sécuriser en production)
    """
    return {
        "active_connections": len(manager.active_connections),
        "users": list(manager.active_connections.keys())
    }


@realtime_router.post("/broadcast")
async def broadcast_message(
    message: str,
    current_user: User = Depends(get_current_user)
):
    """
    Envoie un message à tous les utilisateurs connectés.
    (Admin only - à sécuriser en production)
    """
    count = 0
    for user_id in list(manager.active_connections.keys()):
        await manager.send_message(user_id, {
            "type": "broadcast",
            "message": message,
            "timestamp": datetime.now(UTC).isoformat()
        })
        count += 1

    return {
        "sent_to": count,
        "message": "Broadcast envoyé"
    }

