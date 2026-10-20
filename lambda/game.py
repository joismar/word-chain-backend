import random
import unicodedata
import uuid
from typing import Callable

from aws_lambda_powertools import Logger

from entities.player import Player, PlayerColor, PlayerStatus
from entities.session import GameConfig, GameStatus, Session, Word
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository
from messages.messages_pt import ErrorMessage
from protocol import models as wire
from protocol.mapping import game_state, player_view
from utils import wordlist
from utils.calculate_score import calculate_score
from utils.errors import ConcurrentUpdateError, GameException

logger = Logger(child=True)


def normalize(text: str) -> str:
    """Lowercase without accents, matching the wordlist and room names."""
    decomposed = unicodedata.normalize('NFD', text.strip().lower())
    return ''.join(c for c in decomposed if not unicodedata.combining(c))


class Game:
    """Handles one protocol v2 message for one connection at one instant.

    Every handler reloads state, so the whole call can be retried after a
    ConcurrentUpdateError. Deadlines are applied before anything else.
    """

    def __init__(self, session_repository: ISessionRepository,
                 player_repository: IPlayerRepository, gateway,
                 connection_id: str, now: int,
                 words_loader: Callable = wordlist.load) -> None:
        self.session_repository = session_repository
        self.player_repository = player_repository
        self.gateway = gateway
        self.connection_id = connection_id
        self.now = now
        self.words_loader = words_loader

    def handle(self, message):
        handler = getattr(self, f'_on_{message.type}')
        return handler(message)

    # ------------------------------------------------------------ lobby

    def _on_host(self, message: wire.HostMessage):
        _, _, five_letter_words = self.words_loader()
        session = Session(random.choice(five_letter_words), _id=str(uuid.uuid4()))
        player = Player(message.payload.player_name, _id=self.connection_id,
                        session_id=session.id, color=random.choice(list(PlayerColor)))
        session.players.append(player)
        self.session_repository.save(session)
        return self.__session_reply(message, player, session)

    def _on_join(self, message: wire.JoinMessage):
        session = self.session_repository.get_by_name(normalize(message.payload.room_name))
        if session.status != GameStatus.CREATED:
            raise GameException(ErrorMessage.GAME_STARTED)

        player = session.find_player(self.connection_id)
        if player is None:
            used = {p.color for p in session.players}
            free = [color for color in PlayerColor if color not in used]
            if not free:
                raise GameException(ErrorMessage.ROOM_FULL)
            player = Player(message.payload.player_name, _id=self.connection_id,
                            session_id=session.id, color=random.choice(free))
            session.players.append(player)
            self.__commit(session)
        return self.__session_reply(message, player, session)

    def _on_ready(self, message: wire.ReadyMessage):
        player, session, _ = self.__load()
        if session.status != GameStatus.CREATED:
            raise GameException(ErrorMessage.GAME_STARTED)
        player.status = PlayerStatus.READY if message.payload.ready else PlayerStatus.WAITING
        self.__commit(session)
        return self.__ack(message)

    def _on_start(self, message: wire.StartMessage):
        player, session, _ = self.__load()
        if session.host is not player:
            raise GameException(ErrorMessage.NOT_HOST)
        if session.status != GameStatus.CREATED:
            raise GameException(ErrorMessage.GAME_STARTED)
        if not all(p.status == PlayerStatus.READY for p in session.players):
            raise GameException(ErrorMessage.ALL_PLAYERS_NEED_READY)

        _, word_list, _ = self.words_loader()
        config = GameConfig(time=message.payload.config.time,
                            repetition=message.payload.config.repetition)
        session.start(config, random.choice(word_list), self.now)
        self.__commit(session)
        return self.__ack(message)

    # ------------------------------------------------------------ turns

    def _on_word(self, message: wire.WordMessage):
        player, session, _ = self.__load()
        self.__require_turn(player, session)

        word = normalize(message.payload.word)
        words, _, _ = self.words_loader()
        if word not in words:
            raise GameException(ErrorMessage.INEXISTENT_WORD)

        played = [item.word for item in session.chain]
        if word in played and not session.config.repetition:
            # Playing a used word costs the turn.
            session.advance_turn(self.now)
            self.__commit(session)
            raise GameException(ErrorMessage.WORD_ALREADY_IN_GAME)

        points = calculate_score(played[-1], word)
        if points == 0:
            raise GameException(ErrorMessage.NO_POINTS)
        # Bonus when the new word also links back into the previous one.
        chain_points = calculate_score(word, played[-1])

        player.give_score(points + chain_points)
        session.chain.append(Word(word, player.id))
        session.advance_turn(self.now)
        self.__commit(session)
        return wire.AckMessage(request_id=message.request_id,
                               payload=wire.AckPayload(points=points, chain_points=chain_points))

    def _on_pass(self, message: wire.PassMessage):
        player, session, _ = self.__load()
        self.__require_turn(player, session)
        session.advance_turn(self.now)
        self.__commit(session)
        return self.__ack(message)

    def _on_timeout(self, message: wire.TimeoutMessage):
        _, _, expired = self.__load()
        if not expired:
            raise GameException(ErrorMessage.DEADLINE_NOT_REACHED)
        return self.__ack(message)

    # ------------------------------------------------------ connections

    def _on_reconnect(self, message: wire.ReconnectMessage):
        old_id = message.payload.player_id
        stored = self.player_repository.get(old_id)
        session = self.session_repository.get(stored.session_id)
        player = session.find_player(old_id)
        if player is None:
            raise GameException(ErrorMessage.INEXISTENT_PLAYER)

        if old_id != self.connection_id:
            session.apply_deadlines(self.now)
            player.id = self.connection_id
            player.status = (PlayerStatus.READY if session.status == GameStatus.CREATED
                             else PlayerStatus.IN_GAME)
            self.__commit(session)
            self.player_repository.delete(old_id)
        return self.__session_reply(message, player, session)

    def disconnect(self):
        try:
            stored = self.player_repository.get(self.connection_id)
            session = self.session_repository.get(stored.session_id)
        except GameException:
            return
        player = session.find_player(self.connection_id)
        if player is None or player.status == PlayerStatus.OFFLINE:
            return
        player.status = PlayerStatus.OFFLINE
        session.apply_deadlines(self.now)
        self.__commit(session)

    # ---------------------------------------------------------- helpers

    def __load(self):
        """Returns (player, session, deadlines_expired) for this connection."""
        stored = self.player_repository.get(self.connection_id)
        session = self.session_repository.get(stored.session_id)
        player = session.find_player(self.connection_id)
        if player is None:
            raise GameException(ErrorMessage.INEXISTENT_PLAYER)
        expired = session.apply_deadlines(self.now)
        if expired:
            # Persist now: the request itself may still fail (e.g. its turn
            # just ran out) and the expiry must not be lost with it.
            self.__commit(session)
        return player, session, expired

    def __require_turn(self, player: Player, session: Session):
        if session.status == GameStatus.FINISHED:
            raise GameException(ErrorMessage.GAME_FINISHED)
        if session.status != GameStatus.STARTED or self.now < session.started_at:
            raise GameException(ErrorMessage.GAME_NOT_STARTED)
        if session.turn_player is not player:
            raise GameException(ErrorMessage.INVALID_TURN)

    def __commit(self, session: Session):
        self.session_repository.save(session)
        self.__broadcast(session)

    def __broadcast(self, session: Session):
        gone = self.gateway.broadcast(self.__online_ids(session), self.__state_message(session))
        if not gone:
            return

        for player in session.players:
            if player.id in gone:
                player.status = PlayerStatus.OFFLINE
        session.apply_deadlines(self.now)
        try:
            self.session_repository.save(session)
        except ConcurrentUpdateError:
            # Someone else moved the session on; their broadcast will retry.
            logger.info('skipped marking gone connections offline', extra={'gone': gone})
            return
        self.gateway.broadcast(self.__online_ids(session), self.__state_message(session))

    def __online_ids(self, session: Session) -> list[str]:
        return [p.id for p in session.players if p.status != PlayerStatus.OFFLINE]

    def __state_message(self, session: Session) -> dict:
        return wire.to_wire(wire.GameStateMessage(payload=game_state(session, self.now)))

    def __session_reply(self, message, player: Player, session: Session):
        return wire.SessionMessage(
            request_id=message.request_id,
            payload=wire.SessionPayload(player=player_view(player),
                                        game=game_state(session, self.now)))

    @staticmethod
    def __ack(message):
        return wire.AckMessage(request_id=message.request_id, payload=wire.AckPayload())
