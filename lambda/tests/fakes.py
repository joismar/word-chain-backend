"""In-memory stand-ins for DynamoDB and the API Gateway management API.

The repositories come from local.memory (shared with the dev server); the
session fake adds knobs so concurrency paths can be tested without moto.
"""
from local.memory import MemoryPlayerRepository, MemorySessionRepository
from utils.errors import ConcurrentUpdateError

FakePlayerRepository = MemoryPlayerRepository


class FakeSessionRepository(MemorySessionRepository):
    def __init__(self, player_repository):
        super().__init__(player_repository)
        self.saves = 0
        # Number of upcoming saves that should fail as if someone else wrote first.
        self.conflicts_to_raise = 0

    def save(self, session):
        if self.conflicts_to_raise:
            self.conflicts_to_raise -= 1
            raise ConcurrentUpdateError(session.id)
        super().save(session)
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
