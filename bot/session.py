from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from bot.checklist import Question


@dataclass
class Session:
    user_id: str
    channel_id: str
    state: str = "selecting_project"  # "selecting_project" | "answering"
    projects: list = field(default_factory=list)
    project: Optional[dict] = None
    questions: list[Question] = field(default_factory=list)
    current_question: int = 0
    answers: dict[str, str] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.now)


class SessionManager:
    def __init__(self, expiry_minutes: int = 1440) -> None:
        self._sessions: dict[str, Session] = {}
        self._expiry = timedelta(minutes=expiry_minutes)

    def get(self, user_id: str) -> Optional[Session]:
        s = self._sessions.get(user_id)
        if s is None:
            return None
        if datetime.now() - s.last_activity > self._expiry:
            del self._sessions[user_id]
            return None
        return s

    def create(self, user_id: str, channel_id: str, projects: list) -> Session:
        s = Session(user_id=user_id, channel_id=channel_id, projects=projects)
        self._sessions[user_id] = s
        return s

    def touch(self, session: Session) -> None:
        session.last_activity = datetime.now()

    def close(self, user_id: str) -> None:
        self._sessions.pop(user_id, None)
