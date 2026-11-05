"""In-memory repositories with the same contract as the DynamoDB ones.

They store deep copies and enforce the same optimistic version check as
SessionRepository. Used by the unit tests and by the local dev server.
"""
import copy

from messages.messages_pt import ErrorMessage
from utils.errors import ConcurrentUpdateError, GameException


class MemoryPlayerRepository:
    def __init__(self):
        self.items = {}

    def get(self, player_id):
        if player_id not in self.items:
            raise GameException(ErrorMessage.INEXISTENT_PLAYER)
        return copy.deepcopy(self.items[player_id])

    def save(self, player):
        self.items[player.id] = copy.deepcopy(player)

    def delete(self, player_id):
        self.items.pop(player_id, None)

    def get_players_by_session(self, session_id):
        return [copy.deepcopy(p) for p in self.items.values() if p.session_id == session_id]


class MemorySessionRepository:
    def __init__(self, player_repository):
        self.player_repository = player_repository
        self.items = {}

    def get(self, session_id):
        if session_id not in self.items:
            raise GameException(ErrorMessage.INEXISTENT_SESSION)
        session = copy.deepcopy(self.items[session_id])
        session.players = [self.player_repository.get(p.id) for p in session.players
                           if p.id in self.player_repository.items]
        return session

    def get_by_name(self, name):
        for session in self.items.values():
            if session.name == name:
                return self.get(session.id)
        raise GameException(ErrorMessage.INEXISTENT_SESSION)

    def save(self, session):
        stored = self.items.get(session.id)
        if (stored.version if stored else 0) != session.version:
            raise ConcurrentUpdateError(session.id)
        session.version += 1
        self.items[session.id] = copy.deepcopy(session)
        for player in session.players:
            self.player_repository.save(player)
