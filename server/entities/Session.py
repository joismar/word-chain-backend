from enum import Enum
import uuid
from entities.player import Player
from entities.repository_manager import RepositoryManager


class GameStatus(int, Enum):
    CREATED = 0
    STARTED = 1


class Session:
    def __init__(self, name: str, _id=None, players=None, turn_index=0, chain=None, status=GameStatus.CREATED):
        if players is None:
            players = []
        if chain is None:
            chain = []

        self.id: str = _id or str(uuid.uuid4())
        self.name: str = name
        self.players: list[Player] = players
        self.turn_index: int = turn_index
        self.chain: list[str] = chain
        self.status: GameStatus = status

    @property
    def turn_player(self):
        return self.players[self.turn_index]

    def swap_turn(self):
        if self.turn_index == len(self.players) - 1:
            self.turn_index = 0
        else:
            self.turn_index += 1

    def to_dict(self):
        old_players = self.players
        self.players = [x.to_dict() for x in self.players]
        new_dict = self.__dict__.copy()
        self.players = old_players
        return new_dict

    def find_player(self, player_id: str):
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def save(self):
        RepositoryManager.save(self)
