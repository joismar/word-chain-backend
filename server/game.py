import json
import random
from typing import List

from entities.player import Player, PlayerCondition
from entities.session import GameStatus, Session
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository
from messages.messages_pt import Error, Message
from responses.action_response import ActionResponse
from utils.calculate_score import calculate_score


class GameData:
    def __init__(self, status: GameStatus, chain: List[str], players: List[Player], turn: int):
        self.status = status
        self.chain = chain
        self.players = [player.to_dict() for player in players]
        self.turn = turn

    def to_dict(self):
        return self.__dict__


class Game:
    def __init__(self, session_repository: ISessionRepository, player_repository: IPlayerRepository, apigateway_management_api: any=None) -> None:
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

    def host(self, player_name: str):
        session: Session = Session(
            "_".join(random.sample(self.words, 2)), _id=self.connection_id)
        player: Player = Player(
            player_name, _id=self.connection_id, session_id=self.connection_id)
        session.players.append(player)
        session.save()

        return ActionResponse('host', {'player': player.to_dict(), 'game': { 'game_name': session.name, 'status': session.status }})

    def join(self, game_name: str, player_name: str):
        session: Session = self.session_repository.get_by_name(game_name)
        if not session:
            return self.__error('join', Error.INEXISTENT_SESSION)
        player: Player = Player(
            player_name, _id=self.connection_id, session_id=session.id)
        session.players.append(player)
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session.status, session.chain, session.players, session.turn_index).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('join', player.to_dict())

    def condition(self, player_id: str, player_condition: PlayerCondition, session_id: str):
        session: Session = self.session_repository.get(session_id)
        if not session:
            return self.__error('start', Error.INEXISTENT_SESSION)
        player: Player = session.find_player(player_id)
        if not player:
            return self.__error('condition', Error.INEXISTENT_PLAYER)
        player.condition = PlayerCondition(player_condition)
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session.status, session.chain, session.players, session.turn_index).to_dict()),
            [p.id for p in session.players ])

        return ActionResponse('condition', {'success': True})

    def start(self, session_id: str):
        session: Session = self.session_repository.get(session_id)
        if not session:
            return self.__error('start', Error.INEXISTENT_SESSION)
        if not self.__ready_to_start(session):
            return self.__error('start', Error.ALL_PLAYERS_NEED_READY)
        session.status = GameStatus.STARTED
        session.chain.append(random.choice(self.words))
        session.save()

        self.__broadcast(
            ActionResponse(
                'game_data',
                GameData(session.status, session.chain, session.players, session.turn_index).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('start', {'success': True})

    def word(self, session_id: str, player_id: str, word: str):
        session: Session = self.session_repository.get(session_id)
        if not session:
            return self.__error('word', Error.INEXISTENT_SESSION)
        if not session.turn_player.id == player_id:
            return self.__error('word', Error.INVALID_TURN)
        if word not in self.words:
            return self.__error('word', Error.INEXISTENT_WORD)
        if word in session.chain:
            session.swap_turn()
            session.save()
            self.__broadcast(
                ActionResponse(
                    'game_data',
                    GameData(session.status, session.chain, session.players, session.turn_index).to_dict()),
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
                GameData(session.status, session.chain, session.players, session.turn_index).to_dict()),
            [p.id for p in session.players])

        return ActionResponse('word', {'success': True})

    def set_word_time(self, session_id: str, player_id: str, word_time: float):
        session: Session = self.session_repository.get(session_id)
        if not session:
            return self.__error('set_word_time', Error.INEXISTENT_SESSION)
        player: Player = session.find_player(player_id)
        if not player:
            return self.__error('set_word_time', Error.INEXISTENT_PLAYER)

        player.last_word_time = word_time

        session.save()

    def disconnect(self):
        player = self.player_repository.get(self.connection_id)
        session = self.session_repository.get(player.session_id)
        
        if not player:
            return
        if player.session_id == player.id:
            self.__disconnect_all([p.id for p in session.players if player.id != player.session_id])
            self.session_repository.delete(self.connection_id)
        else:
            self.player_repository.delete(self.connection_id)
            self.__broadcast(
                ActionResponse(
                    'game_data',
                    GameData(session.status, session.chain, session.players, session.turn_index).to_dict()),
                [p.id for p in session.players])
        return
            
    def __broadcast(self, action_response: ActionResponse, connections: List[str]):
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
        return all(x.condition == PlayerCondition.READY for x in session.players)

    def __error(self, action: str, error: Error):
        return ActionResponse(action, {"error": True, "message": error.value, "code": error.name})
