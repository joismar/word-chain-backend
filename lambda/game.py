from datetime import datetime, timedelta
import json
import random
from typing import List

from entities.player import Player, PlayerColor, PlayerStatus
from entities.session import GameMode, GameStatus, Session, Word
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository
from messages.messages_pt import Error, Message
from responses.action_response import ActionResponse
from utils.calculate_score import calculate_score


class GameData:
    def __init__(self, session: Session):
        self.status = session.status
        self.chain = [item.to_dict() for item in session.chain]
        self.players = [player.to_dict() for player in session.players]
        self.turn = session.turn_index
        self.name = session.name
        self.started_at = session.started_at

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
        self.connection_id = None

    def load_words(self):
        with open('wordlist.txt', 'r', encoding='utf-8') as f:
            self.words = f.read().split('\n')

    def set_connection_id(self, connection_id: str):
        self.connection_id = connection_id

    def reconnect(self, old_connection_id: str):
        connected_player = self.player_repository.get(old_connection_id)
        if connected_player:
            session = self.session_repository.get(connected_player.session_id)
            if session:
                player = session.find_player(connected_player.id)
                player.status = PlayerStatus.IN_GAME
                player.id = self.connection_id
                session.save()
                self.__broadcast(
                    ActionResponse(
                        'game_data',
                        GameData(session).to_dict()),
                    [p.id for p in session.players])

    def host(self, player_name: str):
        session: Session = Session(
            random.choice(self.words), _id=self.connection_id)
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
            return self.__error('join', Error.GAME_STARTED)
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
            return self.__error('join', Error.GAME_STARTED)

        player = session.find_player(self.connection_id)
        player.status = PlayerStatus(int(player_status))
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('status', {'success': True})

    def start(self, mode: GameMode):
        session: Session = self.session_repository.get(self.connection_id)

        if not self.__ready_to_start(session):
            return self.__error('start', Error.ALL_PLAYERS_NEED_READY)

        for player in session.players:
            player.status = PlayerStatus.IN_GAME

        session.status = GameStatus.STARTED
        session.chain.append(Word(random.choice(self.words), player.id))
        session.game_mode = GameMode(int(mode))
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
            return self.__error('word', Error.INVALID_TURN)

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
            return self.__error('word', Error.INVALID_TURN)

        if word not in self.words:
            return self.__error('word', Error.INEXISTENT_WORD)

        word_list = [item.word for item in session.chain]
        if word in word_list:
            session.swap_turn()
            session.save()
            self.__broadcast(
                ActionResponse(
                    'game_data',
                    GameData(session).to_dict()),
                [p.id for p in session.players])
            return self.__error('word', Error.WORD_ALREADY_IN_GAME)

        score = calculate_score(word_list[-1], word)
        chain_score = calculate_score(word, word_list[-1])

        if score == 0:
            return self.__error('word', Error.NO_POINTS)

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
        player = self.player_repository.get(self.connection_id)
        session = self.session_repository.get(player.session_id)

        if not player:
            return

        player = session.find_player(self.connection_id)
        player.status = PlayerStatus.OFFLINE
        session.save()
        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players if p.id != self.connection_id])

    def get_session_active_colors(self, session: Session):
        return [player.color for player in session.players]

    def end_game(self):
        connected_player = self.player_repository.get(self.connection_id)
        session: Session = self.session_repository.get(
            connected_player.session_id)

        if session.id != connected_player.id:
            return self.__error('end', Error.END_GAME_PERMISSION)

        session.status = GameStatus.FINISHED
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

    def __broadcast(self, action_response: ActionResponse,
                    connections: List[str]):
        client = self.apigateway_management_api
        for connection in connections:
            client.post_to_connection(
                Data=json.dumps({'action': action_response.action,
                                'data': action_response.data}).encode('gbk'),
                ConnectionId=connection
            )

    def __disconnect_all(self, connections: List[str]):
        client = self.apigateway_management_api
        for connection in connections:
            client.delete_connection(
                ConnectionId=connection
            )

    def __ready_to_start(self, session: Session):
        return all(x.status == PlayerStatus.READY for x in
                   session.players)

    def __error(self, action: str, error: Error):
        return ActionResponse(
            action,
            {"error": True, "message": error.value, "code": error.name})
