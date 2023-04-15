from enum import Enum
import uuid
from entities.Player import Player


class GameStatus(int, Enum):
  CREATED = 0
  STARTED = 1

class Session:
  def __init__(self, name, id=None, players=[], turn_index=0, chain=None, status=GameStatus.CREATED):
    self.id: str = id or str(uuid.uuid4())
    self.name: str = name
    self.players: list[Player] = players
    self.turn_index: int = turn_index
    self.chain: list[str] = chain
    self.status: GameStatus = status

  def turn_player(self):
    return self.players[self.turn_index]

  def swap_turn(self):
    if self.turn_index == len(self.players) - 1:
      self.turn_index = 0
    else:
      self.turn_index += 1

  def to_dict(self):
    old_players = self.players
    self.players = list(map(lambda x: x.to_dict(), self.players))
    new_dict = self.__dict__.copy()
    self.players = old_players
    return new_dict
  
  def find_player(self, player_id: str):
    for player in self.players:
      if player.id == player_id: 
        return player
