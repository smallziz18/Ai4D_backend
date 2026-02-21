"""
Modèles de base de données pour les agents IA.
Ces modèles sont automatiquement pris en compte par Alembic.
"""
from typing import Dict, Any, List
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text
import sqlalchemy.dialects.postgresql as pg


class AgentContext(SQLModel, table=True):
    """
    Contexte partagé entre tous les agents multi-agents.
    Stocke l'historique des interactions, décisions et états.
    """
    __tablename__ = "agent_contexts"

    id: UUID = Field(
        sa_column=Column(
            pg.UUID,
            primary_key=True,
            default=uuid4
        )
    )

    user_id: str = Field(
        sa_column=Column(
            Text,
            nullable=False,
            index=True
        )
    )

    session_id: str = Field(
        sa_column=Column(
            Text,
            nullable=False,
            index=True
        )
    )

    # Contexte actuel (état du workflow)
    current_state: str = Field(
        sa_column=Column(
            Text,
            default="idle"
        )
    )

    current_agent: str | None = Field(
        sa_column=Column(
            Text,
            nullable=True
        ),
        default=None
    )

    # Données contextuelles (JSON)
    context_data: Dict[str, Any] = Field(
        sa_column=Column(
            JSON,
            default=dict
        ),
        default_factory=dict
    )

    conversation_history: List[Dict[str, Any]] = Field(
        sa_column=Column(
            JSON,
            default=list
        ),
        default_factory=list
    )

    # Métriques et suivi
    total_interactions: int = Field(
        sa_column=Column(
            pg.INTEGER,
            default=0
        ),
        default=0
    )

    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow
        )
    )

    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=datetime.utcnow,
            onupdate=datetime.utcnow
        )
    )

    # Métadonnées supplémentaires
    meta_data: Dict[str, Any] = Field(
        sa_column=Column(
            JSON,
            default=dict
        ),
        default_factory=dict
    )

    def __repr__(self) -> str:
        return f"AgentContext(id={self.id}, user_id={self.user_id}, session_id={self.session_id})"

    class Config:
        arbitrary_types_allowed = True

