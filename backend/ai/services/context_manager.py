"""
ConversationContextManager — maintains active conversation memory across user turns.

Tracks active session context such as:
- active_case_id (CaseMasterID or FIR reference)
- active_district
- active_crime_head
- active_police_station
- active_status
- last_intent
- last_question
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

_logger = logging.getLogger("backend.ai.services.context_manager")


@dataclass
class ConversationState:
    session_id: str
    active_case_id: int | None = None
    active_fir_number: str | None = None
    active_district: str | None = None
    active_crime_head: str | None = None
    active_police_station: str | None = None
    active_status: str | None = None
    last_intent: str | None = None
    last_question: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_case_id": self.active_case_id,
            "active_fir_number": self.active_fir_number,
            "active_district": self.active_district,
            "active_crime_head": self.active_crime_head,
            "active_police_station": self.active_police_station,
            "active_status": self.active_status,
            "last_intent": self.last_intent,
            "last_question": self.last_question,
        }


class ConversationContextManager:
    """In-memory store for active session states."""

    _instances: dict[str, ConversationContextManager] = {}

    def __init__(self) -> None:
        self._store: dict[str, ConversationState] = {}

    @classmethod
    def get_instance(cls) -> ConversationContextManager:
        if "default" not in cls._instances:
            cls._instances["default"] = ConversationContextManager()
        return cls._instances["default"]

    def get_state(self, session_id: str | None) -> ConversationState:
        sid = session_id or "default_session"
        if sid not in self._store:
            self._store[sid] = ConversationState(session_id=sid)
        return self._store[sid]

    def update_state(
        self,
        session_id: str | None,
        *,
        case_id: int | None = None,
        fir_number: str | None = None,
        district: str | None = None,
        crime_head: str | None = None,
        police_station: str | None = None,
        status: str | None = None,
        intent: str | None = None,
        question: str | None = None,
    ) -> ConversationState:
        state = self.get_state(session_id)
        if case_id is not None:
            state.active_case_id = case_id
        if fir_number is not None:
            state.active_fir_number = fir_number
        if district is not None:
            state.active_district = district
        if crime_head is not None:
            state.active_crime_head = crime_head
        if police_station is not None:
            state.active_police_station = police_station
        if status is not None:
            state.active_status = status
        if intent is not None:
            state.last_intent = intent
        if question is not None:
            state.last_question = question
        state.updated_at = datetime.now(timezone.utc)
        return state

    def clear_state(self, session_id: str | None) -> None:
        sid = session_id or "default_session"
        if sid in self._store:
            del self._store[sid]


def get_context_manager() -> ConversationContextManager:
    return ConversationContextManager.get_instance()
