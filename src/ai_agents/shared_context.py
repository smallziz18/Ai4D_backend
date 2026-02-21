"""
Contexte partagé entre tous les agents multi-agents.
Stocké dans PostgreSQL pour persistence et dans Redis pour performance.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import json as json_lib

from src.config import Config
from src.db.redis import r as redis_client
from src.ai_agents.models import AgentContext


class SharedContextService:
    """Service pour gérer le contexte partagé entre agents"""

    def __init__(self):
        # Utiliser une URL synchrone pour SQLAlchemy classique
        sync_database_url = Config.DATABASE_URL.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql+psycopg2")
        self.engine = create_engine(sync_database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.redis_client = redis_client

    def get_session(self) -> Session:
        """Obtenir une session SQLAlchemy"""
        return self.SessionLocal()

    def list_contexts(self, user_id: str) -> list:
        """Lister les contextes (sessions) pour un utilisateur."""
        session = self.get_session()
        try:
            rows = session.query(AgentContext).filter(AgentContext.user_id == user_id).order_by(AgentContext.created_at.desc()).all()
            out = []
            for r in rows:
                out.append({
                    "session_id": r.session_id,
                    "context_id": r.id,
                    "current_state": r.current_state,
                    "current_agent": r.current_agent,
                    "total_interactions": r.total_interactions,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat()
                })
            return out
        finally:
            session.close()

    def delete_context(self, user_id: str, session_id: str) -> bool:
        """Supprimer un contexte (session) spécifique."""
        session = self.get_session()
        try:
            ctx = session.query(AgentContext).filter(AgentContext.user_id == user_id, AgentContext.session_id == session_id).first()
            if not ctx:
                return False
            session.delete(ctx)
            session.commit()
            # Purger le cache Redis
            cache_key = f"agent_context:{user_id}:{session_id}"
            try:
                import asyncio
                # Redis client est async; appel via boucle si nécessaire
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.redis_client.delete(cache_key))
                else:
                    loop.run_until_complete(self.redis_client.delete(cache_key))
            except Exception:
                pass
            return True
        finally:
            session.close()


    async def get_context(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupérer le contexte pour un utilisateur et une session.
        Vérifie d'abord Redis, puis PostgreSQL.
        """
        cache_key = f"agent_context:{user_id}:{session_id}"

        # 1. Vérifier Redis
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json_lib.loads(cached)
        except Exception as e:
            print(f"Redis error: {e}")

        # 2. Vérifier PostgreSQL
        session = self.get_session()
        try:
            context = session.query(AgentContext).filter(
                AgentContext.user_id == user_id,
                AgentContext.session_id == session_id
            ).first()

            if context:
                context_dict = {
                    "id": context.id,
                    "user_id": context.user_id,
                    "session_id": context.session_id,
                    "current_state": context.current_state,
                    "current_agent": context.current_agent,
                    "context_data": context.context_data,
                    "conversation_history": context.conversation_history,
                    "total_interactions": context.total_interactions,
                    "created_at": context.created_at.isoformat(),
                    "updated_at": context.updated_at.isoformat(),
                    "meta_data": context.meta_data
                }

                # Mettre en cache dans Redis (expire après 1h)
                try:
                    await self.redis_client.setex(
                        cache_key,
                        3600,
                        json_lib.dumps(context_dict)
                    )
                except Exception as e:
                    print(f"Redis cache error: {e}")

                return context_dict

            return None
        finally:
            session.close()

    async def create_context(
        self,
        user_id: str,
        session_id: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Créer un nouveau contexte"""
        session = self.get_session()
        try:
            context = AgentContext(
                user_id=user_id,
                session_id=session_id,
                current_state="idle",
                context_data=initial_data or {},
                conversation_history=[],
                total_interactions=0
            )
            session.add(context)
            session.commit()
            session.refresh(context)

            context_dict = {
                "id": context.id,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "current_state": context.current_state,
                "current_agent": context.current_agent,
                "context_data": context.context_data,
                "conversation_history": context.conversation_history,
                "total_interactions": context.total_interactions,
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "meta_data": context.meta_data
            }

            # Mettre en cache
            cache_key = f"agent_context:{user_id}:{session_id}"
            try:
                await self.redis_client.setex(
                    cache_key,
                    3600,
                    json_lib.dumps(context_dict)
                )
            except Exception as e:
                print(f"Redis cache error: {e}")

            return context_dict
        finally:
            session.close()

    async def update_context(
        self,
        user_id: str,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mettre à jour le contexte"""
        session = self.get_session()
        try:
            context = session.query(AgentContext).filter(
                AgentContext.user_id == user_id,
                AgentContext.session_id == session_id
            ).first()

            if not context:
                return None

            # Mettre à jour les champs
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)

            context.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(context)

            context_dict = {
                "id": context.id,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "current_state": context.current_state,
                "current_agent": context.current_agent,
                "context_data": context.context_data,
                "conversation_history": context.conversation_history,
                "total_interactions": context.total_interactions,
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "meta_data": context.meta_data
            }

            # Invalider le cache Redis
            cache_key = f"agent_context:{user_id}:{session_id}"
            try:
                await self.redis_client.delete(cache_key)
                await self.redis_client.setex(
                    cache_key,
                    3600,
                    json_lib.dumps(context_dict)
                )
            except Exception as e:
                print(f"Redis cache error: {e}")

            return context_dict
        finally:
            session.close()

    async def add_message(
        self,
        user_id: str,
        session_id: str,
        agent: str,
        message: str,
        message_type: str = "agent"  # agent, user, system
    ) -> Optional[Dict[str, Any]]:
        """Ajouter un message à l'historique de conversation"""
        context = await self.get_context(user_id, session_id)
        if not context:
            return None

        conversation_history = context.get("conversation_history", [])
        conversation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "type": message_type,
            "message": message
        })

        return await self.update_context(
            user_id,
            session_id,
            {
                "conversation_history": conversation_history,
                "total_interactions": context.get("total_interactions", 0) + 1
            }
        )

    async def get_or_create_context(
        self,
        user_id: str,
        session_id: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Récupérer ou créer un contexte"""
        context = await self.get_context(user_id, session_id)
        if context:
            return context
        return await self.create_context(user_id, session_id, initial_data)


# Instance globale
shared_context_service = SharedContextService()
