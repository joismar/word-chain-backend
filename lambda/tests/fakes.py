"""In-memory stand-ins for DynamoDB and the API Gateway management API.

The session fake stores deep copies and enforces the same optimistic
version check as SessionRepository, so concurrency paths can be tested
without moto.
"""
import copy

from messages.messages_pt import ErrorMessage
from utils.errors import ConcurrentUpdateError, GameException


class FakePlayerRepository:
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


class FakeSessionRepository:
    def __init__(self, player_repository):
        self.player_repository = player_repository
        self.items = {}
        self.saves = 0
        # Number of upcoming saves that should fail as if someone else wrote first.
        self.conflicts_to_raise = 0

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
        if self.conflicts_to_raise:
            self.conflicts_to_raise -= 1
            raise ConcurrentUpdateError(session.id)
        stored = self.items.get(session.id)
        if (stored.version if stored else 0) != session.version:
            raise ConcurrentUpdateError(session.id)
        session.version += 1
        self.items[session.id] = copy.deepcopy(session)
        for player in session.players:
            self.player_repository.save(player)
        self.saves += 1


class FakeGateway:
    def __init__(self):
        self.sent = []  # (connection_id, message)
        self.gone = set()

    def send(self, connection_id, message):
        self.sent.append((connection_id, message))
        return connection_id not in self.gone

    def broadcast(self, connection_ids, message):
        for connection_id in connection_ids:
            self.sent.append((connection_id, message))
        return [cid for cid in connection_ids if cid in self.gone]

    def messages_to(self, connection_id, type_=None):
        return [m for cid, m in self.sent
                if cid == connection_id and (type_ is None or m['type'] == type_)]

    def last_state(self, connection_id):
        states = self.messages_to(connection_id, 'game_state')
        return states[-1]['payload'] if states else None
