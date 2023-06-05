from enum import Enum
import uuid


class PlayerStatus(int, Enum):
    WAITING = 0
    READY = 1


class Player:
    def __init__(
            self, name, _id=None, score=0, status=PlayerStatus.WAITING,
            session_id: str = None, last_word_time: float = 0):
        self.id: str = _id or str(uuid.uuid4())
        self.session_id: str = session_id
        self.name: str = name
        self.score: int = score
        self.status: PlayerStatus = status
        self.last_word_time: float = last_word_time

    def give_score(self, score):
        self.score += score

    def to_dict(self):
        return self.__dict__
