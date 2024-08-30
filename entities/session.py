from enum import Enum
import uuid
from entities.player import Player, PlayerStatus
from entities.repository_manager import RepositoryManager


class GameStatus(int, Enum):
    CREATED = 0
    STARTED = 1


class Word:
    def __init__(self, word: str, player_id: str):
        self.word: str = word
        self.player_id: str = player_id

    def to_dict(self):
        return self.__dict__.copy()


class Session:
    def __init__(
            self, name: str, _id=None, players=None, turn_index=0, chain=None,
            status=GameStatus.CREATED):
        if players is None:
            players = []
        if chain is None:
            chain = []

        self.id: str = _id or str(uuid.uuid4())
        self.name: str = name
        self.players: list[Player] = players
        self.turn_index: int = turn_index
        self.chain: list[Word] = chain
        self.status: GameStatus = status

    @property
    def turn_player(self):
        return self.players[self.turn_index]

    def swap_turn(self):
        if self.turn_index == len(self.players) - 1:
            self.turn_index = 0
        else:
            self.turn_index += 1

        if self.turn_player.status == PlayerStatus.OFFLINE:
            self.swap_turn()

    def to_dict(self):
        old_players = self.players
        old_chain = self.chain
        self.players = [x.to_dict() for x in self.players]
        self.chain = [x.to_dict() for x in self.chain]
        new_dict = self.__dict__.copy()
        self.players = old_players
        self.chain = old_chain
        return new_dict

    def find_player(self, player_id: str):
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def save(self):
        RepositoryManager.save(self)
