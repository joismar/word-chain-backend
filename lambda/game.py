from datetime import datetime, timedelta
import json
import random
from typing import List

from entities.player import Player, PlayerColor, PlayerStatus
from entities.session import GameConfig, GameStatus, Session, Word
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository
from messages.messages_pt import ErrorMessage, Message
from responses.action_response import ActionResponse
from utils.calculate_score import calculate_score
from utils.errors import GameException
from utils import wordlist

MIN_GAME_MINUTES = 1
MAX_GAME_MINUTES = 30


class GameData:
    def __init__(self, session: Session):
        self.status = session.status
        self.chain = [item.to_dict() for item in session.chain]
        self.players = [player.to_dict() for player in session.players]
        self.turn = session.turn_index
        self.name = session.name
        self.started_at = session.started_at
        self.config = session.config.to_dict()

    def to_dict(self):
        return self.__dict__


class Game:
    def __init__(self, session_repository: ISessionRepository,
                 player_repository: IPlayerRepository,
                 apigateway_management_api: any = None) -> None:
        self.session_repository: ISessionRepository = session_repository
        self.player_repository: IPlayerRepository = player_repository
        self.apigateway_management_api = apigateway_management_api
        self.words = None
        self.word_list = None
        self.five_letters_words = None
        self.connection_id = None

    def load_words(self):
        self.words, self.word_list, self.five_letters_words = wordlist.load()

    def set_connection_id(self, connection_id: str):
        self.connection_id = connection_id

    def reconnect(self, old_connection_id: str):
        connected_player = self.player_repository.get(old_connection_id)
        if not connected_player:
            raise GameException(ErrorMessage.INEXISTENT_PLAYER)

        session = self.session_repository.get(connected_player.session_id)
        if not session:
            raise GameException(ErrorMessage.INEXISTENT_SESSION)

        player = session.find_player(connected_player.id)
        if not player:
            raise GameException(ErrorMessage.INEXISTENT_PLAYER)

        self.player_repository.delete(old_connection_id)

        player.id = self.connection_id
        player.status = PlayerStatus.IN_GAME if session.status == GameStatus.STARTED else PlayerStatus.READY
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse(
            'reconnect',
            {'player': player.to_dict(),
             'game': GameData(session).to_dict()})

    def host(self, player_name: str):
        session: Session = Session(
            random.choice(self.five_letters_words), _id=self.connection_id)
        unused_colors = list(PlayerColor)
        player: Player = Player(
            player_name, _id=self.connection_id, session_id=self.connection_id, color=random.choice(unused_colors))
        session.players.append(player)

        session.save()

        return ActionResponse(
            'host',
            {'player': player.to_dict(),
             'game': GameData(session).to_dict()})

    def join(self, game_name: str, player_name: str):
        session: Session = self.session_repository.get_by_name(game_name)

        if session.status == GameStatus.STARTED:
            raise GameException(ErrorMessage.GAME_STARTED)
        session_colors = self.get_session_active_colors(session)
        unused_colors = [
            color for color in PlayerColor if color not in session_colors]
        player: Player = Player(
            player_name, _id=self.connection_id, session_id=session.id, color=random.choice(unused_colors))
        session.players.append(player)
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('join', player.to_dict())

    def status(self, player_status: PlayerStatus):
        connected_player = self.player_repository.get(self.connection_id)
        session = self.session_repository.get(
            connected_player.session_id)

        if session.status == GameStatus.STARTED:
            raise GameException(ErrorMessage.GAME_STARTED)

        player = session.find_player(self.connection_id)
        player.status = PlayerStatus(int(player_status))
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('status', {'success': True})

    def start(self, time: str, repetition: str):
        config = self.__parse_config(time, repetition)
        session: Session = self.session_repository.get(self.connection_id)

        if not self.__ready_to_start(session):
            raise GameException(ErrorMessage.ALL_PLAYERS_NEED_READY)

        for player in session.players:
            player.status = PlayerStatus.IN_GAME

        session.status = GameStatus.STARTED
        session.chain.append(Word(random.choice(self.word_list), player.id))
        session.config = config
        session.started_at = int(
            (datetime.now() + timedelta(seconds=5)).timestamp())
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('start', {'success': True})

    def pass_turn(self):
        connected_player = self.player_repository.get(self.connection_id)
        session: Session = self.session_repository.get(
            connected_player.session_id)

        if not session.turn_player.id == connected_player.id:
            raise GameException(ErrorMessage.INVALID_TURN)

        session.swap_turn()
        session.save()
        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])
        return ActionResponse('word', {'success': True})

    def word(self, word: str):
        connected_player = self.player_repository.get(self.connection_id)

        session: Session = self.session_repository.get(
            connected_player.session_id)

        if not session.turn_player.id == connected_player.id:
            raise GameException(ErrorMessage.INVALID_TURN)

        if word not in self.words:
            raise GameException(ErrorMessage.INEXISTENT_WORD)

        word_list = [item.word for item in session.chain]
        if word in word_list and not session.config.repetition:
            session.swap_turn()
            session.save()
            self.__broadcast(
                ActionResponse(
                    'game_data',
                    GameData(session).to_dict()),
                [p.id for p in session.players])
            raise GameException(ErrorMessage.WORD_ALREADY_IN_GAME)

        score = calculate_score(word_list[-1], word)
        chain_score = calculate_score(word, word_list[-1])

        if score == 0:
            raise GameException(ErrorMessage.NO_POINTS)

        session.turn_player.give_score(chain_score + score)
        session.chain.append(Word(word, connected_player.id))
        session.swap_turn()

        messages = [Message.POINTS.value.format(score)]
        if chain_score > 0:
            messages.append(Message.CHAINED.value.format(chain_score))

        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('word', {'success': True})

    def set_word_time(self, word_time: float):
        connected_player = self.player_repository.get(self.connection_id)
        session: Session = self.session_repository.get(
            connected_player.session_id)

        connected_player.last_word_time = word_time

        session.save()

    def disconnect(self):
        try:
            player = self.player_repository.get(self.connection_id)
            if not player:
                return

            session = self.session_repository.get(player.session_id)
            if not session:
                return

            player = session.find_player(self.connection_id)
            if not player:
                return

            player.status = PlayerStatus.OFFLINE
            session.save()
            self.__broadcast(
                ActionResponse(
                    'game_data',
                    GameData(session).to_dict()),
                [p.id for p in session.players if p.id != self.connection_id])
        except Exception:
            pass

    def get_session_active_colors(self, session: Session):
        return [player.color for player in session.players]

    def end_game(self):
        connected_player = self.player_repository.get(self.connection_id)
        session: Session = self.session_repository.get(
            connected_player.session_id)

        if not session.players or session.players[0].id != connected_player.id:
            raise GameException(ErrorMessage.END_GAME_PERMISSION)

        session.status = GameStatus.FINISHED
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('end', {'success': True})

    def __broadcast(self, action_response: ActionResponse,
                    connections: List[str]):
        client = self.apigateway_management_api
        if not client:
            return
        for connection in connections:
            try:
                client.post_to_connection(
                    Data=json.dumps({'action': action_response.action,
                                    'data': action_response.data}).encode('utf-8'),
                    ConnectionId=connection
                )
            except Exception:
                pass

    def __disconnect_all(self, connections: List[str]):
        client = self.apigateway_management_api
        if not client:
            return
        for connection in connections:
            try:
                client.delete_connection(
                    ConnectionId=connection
                )
            except Exception:
                pass

    @staticmethod
    def __parse_config(time: str, repetition: str) -> GameConfig:
        try:
            minutes = int(time)
        except (TypeError, ValueError):
            raise GameException(ErrorMessage.INVALID_CONFIG)
        if not MIN_GAME_MINUTES <= minutes <= MAX_GAME_MINUTES:
            raise GameException(ErrorMessage.INVALID_CONFIG)
        if repetition not in ('true', 'false'):
            raise GameException(ErrorMessage.INVALID_CONFIG)
        return GameConfig(time=minutes, repetition=repetition == 'true')

    def __ready_to_start(self, session: Session):
        return all(x.status == PlayerStatus.READY for x in
                   session.players)
