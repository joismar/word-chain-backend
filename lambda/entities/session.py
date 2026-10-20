from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional
import uuid
from entities.player import Player, PlayerStatus

START_COUNTDOWN_MS = 5_000
TURN_MS = 15_000
MINUTE_MS = 60_000


class GameStatus(int, Enum):
    CREATED = 0
    STARTED = 1
    FINISHED = 2


@dataclass(frozen=True)
class GameConfig:
    time: int = 3
    repetition: bool = True

    def to_dict(self):
        return asdict(self)


class Word:
    def __init__(self, word: str, player_id: Optional[str]):
        self.word: str = word
        self.player_id: Optional[str] = player_id

    def to_dict(self):
        return self.__dict__.copy()


class Session:
    """A room. Deadlines are owned by the server and stored as epoch ms."""

    def __init__(
            self, name: str, _id=None, players=None, turn_index=0, chain=None,
            status=GameStatus.CREATED, config=None, started_at=None,
            ends_at=None, turn_deadline=None, version=0):

        self.id: str = _id or str(uuid.uuid4())
        self.name: str = name
        self.players: list[Player] = players if players is not None else []
        self.turn_index: int = turn_index
        self.chain: list[Word] = chain if chain is not None else []
        self.status: GameStatus = status
        self.config: GameConfig = config or GameConfig()
        self.started_at: Optional[int] = started_at
        self.ends_at: Optional[int] = ends_at
        self.turn_deadline: Optional[int] = turn_deadline
        # Optimistic lock: the version this object was read at.
        self.version: int = version

    @property
    def host(self) -> Optional[Player]:
        return self.players[0] if self.players else None

    @property
    def turn_player(self) -> Optional[Player]:
        if not self.players:
            return None
        return self.players[self.turn_index % len(self.players)]

    def find_player(self, player_id: str) -> Optional[Player]:
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def start(self, config: GameConfig, first_word: str, now: int):
        for player in self.players:
            player.status = PlayerStatus.IN_GAME
        self.status = GameStatus.STARTED
        self.config = config
        self.chain = [Word(first_word, None)]
        self.turn_index = 0
        self.started_at = now + START_COUNTDOWN_MS
        self.ends_at = self.started_at + config.time * MINUTE_MS
        self.__reset_turn_deadline(self.started_at)

    def advance_turn(self, now: int):
        """The turn player played or passed: next player, fresh turn timer."""
        self.__rotate()
        self.__reset_turn_deadline(now)

    def apply_deadlines(self, now: int) -> bool:
        """Ends the match or passes expired turns. Returns whether anything changed."""
        if self.status != GameStatus.STARTED:
            return False

        if self.ends_at is not None and now >= self.ends_at:
            self.status = GameStatus.FINISHED
            self.turn_deadline = None
            return True

        changed = False
        while self.turn_deadline is not None and now >= self.turn_deadline:
            # Chain from the expired deadline, not from now, so a late
            # request does not hand the next player extra time.
            expired = self.turn_deadline
            self.__rotate()
            self.__reset_turn_deadline(expired)
            changed = True
        return changed

    def __active_players(self) -> list[Player]:
        return [p for p in self.players if p.status != PlayerStatus.OFFLINE]

    def __rotate(self):
        for _ in range(len(self.players)):
            self.turn_index = (self.turn_index + 1) % len(self.players)
            if self.players[self.turn_index].status != PlayerStatus.OFFLINE:
                return

    def __reset_turn_deadline(self, base: int):
        if len(self.__active_players()) > 1:
            self.turn_deadline = base + TURN_MS
        else:
            self.turn_deadline = None
