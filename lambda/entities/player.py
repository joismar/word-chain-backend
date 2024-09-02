from enum import Enum
import uuid


class PlayerStatus(int, Enum):
    WAITING = 0
    READY = 1
    IN_GAME = 2
    OFFLINE = 3

class PlayerColor(int, Enum):
    RED = 0
    BLUE = 1
    GREEN = 2
    YELLOW = 3
    PURPLE = 4
    ORANGE = 5
    PINK = 6
    BROWN = 7

class Player:
    def __init__(
            self, name, _id=None, score=0, status=PlayerStatus.WAITING,
            session_id: str = None, last_word_time: float = 0, color: PlayerColor = None):
        self.id: str = _id or str(uuid.uuid4())
        self.session_id: str = session_id
        self.name: str = name
        self.score: int = score
        self.status: PlayerStatus = status
        self.last_word_time: float = last_word_time
        self.color: PlayerColor = color

    def give_score(self, score):
        self.score += score

    def to_dict(self):
        return self.__dict__
