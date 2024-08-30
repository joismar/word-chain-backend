from entities.session import Session


class ISessionRepository:
    def get(self, session_id: str) -> Session:
        pass

    def save(self, session: Session) -> None:
        pass

    def delete(self, session_id: str) -> None:
        pass

    def get_by_name(self, session_name: str) -> Session:
        pass
