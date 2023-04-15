from entities.Session import Session


class ISessionRepository():
    def get_session(session_id: str) -> Session:
        pass

    def save_session(session: Session) -> None:
        pass