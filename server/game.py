import json
import random
from typing import List

from entities.player import Player, PlayerStatus
from entities.session import GameStatus, Session
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository
from messages.messages_pt import Error, Message
from responses.action_response import ActionResponse
from utils.calculate_score import calculate_score


class GameData:
    def __init__(self, session: Session):
        self.status = session.status
        self.chain = session.chain
        self.players = [player.to_dict() for player in session.players]
        self.turn = session.turn_index
        self.name = session.name

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
            "_".join(random.sample(self.words, 2)), _id=self.connection_id)
        player: Player = Player(
            player_name, _id=self.connection_id, session_id=self.connection_id)
        session.players.append(player)
        session.save()

        return ActionResponse(
            'host',
            {'player': player.to_dict(),
             'game': GameData(session).to_dict()})

    def join(self, game_name: str, player_name: str):
        session: Session = self.session_repository.get_by_name(game_name)
        if not session:
            return self.__error('join', Error.INEXISTENT_SESSION)
        if session.status == GameStatus.STARTED:
            return self.__error('join', Error.GAME_STARTED)
        player: Player = Player(
            player_name, _id=self.connection_id, session_id=session.id)
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
        if not connected_player:
            return self.__error('status', Error.INEXISTENT_PLAYER)
        session = self.session_repository.get(
            connected_player.session_id)
        if not session:
            return self.__error('start', Error.INEXISTENT_SESSION)
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

    def start(self):
        session: Session = self.session_repository.get(self.connection_id)
        if not session:
            return self.__error('start', Error.INEXISTENT_SESSION)
        if not self.__ready_to_start(session):
            return self.__error('start', Error.ALL_PLAYERS_NEED_READY)
        session.status = GameStatus.STARTED
        for player in session.players:
            player.status = PlayerStatus.IN_GAME
        session.chain.append(random.choice(self.words))
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('start', {'success': True})

    def word(self, word: str):
        connected_player = self.player_repository.get(self.connection_id)
        if not connected_player:
            return self.__error('status', Error.INEXISTENT_PLAYER)
        session: Session = self.session_repository.get(
            connected_player.session_id)
        if not session:
            return self.__error('start', Error.INEXISTENT_SESSION)
        if not session.turn_player.id == connected_player.id:
            return self.__error('word', Error.INVALID_TURN)
        if word not in self.words:
            return self.__error('word', Error.INEXISTENT_WORD)
        if word in session.chain:
            session.swap_turn()
            session.save()
            self.__broadcast(
                ActionResponse(
                    'game_data',
                    GameData(session).to_dict()),
                [p.id for p in session.players])
            return self.__error('word', Error.WORD_ALREADY_IN_GAME)

        score = calculate_score(session.chain[-1], word)
        chain_score = calculate_score(word, session.chain[-1])

        if score == 0:
            return self.__error('word', Error.NO_POINTS)

        session.turn_player.give_score(chain_score + score)
        session.chain.append(word)
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
        if not connected_player:
            return self.__error('status', Error.INEXISTENT_PLAYER)
        session: Session = self.session_repository.get(
            connected_player.session_id)
        if not session:
            return self.__error('start', Error.INEXISTENT_SESSION)

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

        return

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
