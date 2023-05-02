from enum import Enum
import uuid


class PlayerCondition(int, Enum):
  WAITING = 0
  READY = 1

class Player:
  def __init__(self, name, _id=None, score=0, condition=PlayerCondition.WAITING):
    self.id: str = _id or str(uuid.uuid4())
    self.name: str = name
    self.score: int = score
    self.condition: PlayerCondition = condition
    self.last_word_time: float

  def give_score(self, score):
    self.score += score

  def to_dict(self):
    return self.__dict__