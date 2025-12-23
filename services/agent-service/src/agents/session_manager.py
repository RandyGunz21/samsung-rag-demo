"""
Session Manager for conversation context.

Manages conversation sessions with history and context.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from collections import OrderedDict
import threading


class ConversationSession:
    """Represents a single conversation session."""

    def __init__(self, session_id: Optional[UUID] = None, max_history: int = 10):
        self.session_id = session_id or uuid4()
        self.created_at = datetime.utcnow()
        self.last_activity = self.created_at
        self.messages: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.title: Optional[str] = None

    def add_message(
        self,
        role: str,
        content: str,
        classification: Optional[str] = None,
        sources: Optional[List[Dict]] = None,
    ) -> str:
        """Add a message to the session."""
        message_id = f"msg_{uuid4().hex[:12]}"

        message = {
            "id": message_id,
            "role": role,
            "content": content,
            "classification": classification,
            "sources": sources,
            "created_at": datetime.utcnow(),
        }

        self.messages.append(message)
        self.last_activity = datetime.utcnow()

        # Set title from first user message
        if role == "user" and not self.title:
            self.title = content[:50] + ("..." if len(content) > 50 else "")

        # Trim old messages
        if len(self.messages) > self.max_history * 2:
            self.messages = self.messages[-self.max_history * 2:]

        return message_id

    def get_context_summary(self) -> str:
        """Get a summary of recent conversation for context."""
        if not self.messages:
            return ""

        recent = self.messages[-6:]  # Last 3 exchanges
        context_parts = []

        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:200]  # Truncate long messages
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    def clear_history(self):
        """Clear conversation history."""
        self.messages = []

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": str(self.session_id),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": self.message_count,
            "title": self.title,
        }


class SessionManager:
    """
    Manages multiple conversation sessions.

    Thread-safe singleton for session management.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_sessions: int = 1000, max_history: int = 10):
        if self._initialized:
            return

        self.max_sessions = max_sessions
        self.max_history = max_history
        self._sessions: OrderedDict[UUID, ConversationSession] = OrderedDict()
        self._lock = threading.Lock()
        self._initialized = True

    def get_or_create_session(self, session_id: Optional[UUID] = None) -> ConversationSession:
        """Get existing session or create new one."""
        with self._lock:
            if session_id and session_id in self._sessions:
                # Move to end (LRU)
                self._sessions.move_to_end(session_id)
                return self._sessions[session_id]

            # Create new session
            session = ConversationSession(
                session_id=session_id,
                max_history=self.max_history
            )

            # Evict old sessions if needed
            while len(self._sessions) >= self.max_sessions:
                self._sessions.popitem(last=False)

            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Get a session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                self._sessions.move_to_end(session_id)
            return session

    def delete_session(self, session_id: UUID) -> bool:
        """Delete a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List all sessions with pagination."""
        with self._lock:
            all_sessions = list(self._sessions.values())
            # Sort by last activity (most recent first)
            all_sessions.sort(key=lambda s: s.last_activity, reverse=True)

            total = len(all_sessions)
            sessions = all_sessions[offset:offset + limit]

            return {
                "sessions": [s.to_dict() for s in sessions],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def get_session_history(
        self,
        session_id: UUID,
        limit: int = 50,
        before: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get session history with pagination."""
        session = self.get_session(session_id)
        if not session:
            return None

        messages = session.messages.copy()

        # Filter by before if provided
        if before:
            before_idx = next(
                (i for i, m in enumerate(messages) if m["id"] == before),
                len(messages)
            )
            messages = messages[:before_idx]

        # Get last N messages
        messages = messages[-limit:]
        has_more = len(session.messages) > len(messages)

        return {
            "session_id": str(session_id),
            "messages": messages,
            "has_more": has_more,
        }


# Singleton getter
def get_session_manager() -> SessionManager:
    """Get session manager singleton."""
    return SessionManager()
