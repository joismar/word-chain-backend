from entities.Session import Session


class ISessionRepository():
    def get_session(self, game_name: str) -> Session:
        pass

    def save_session(self, session: Session) -> None:
        pass