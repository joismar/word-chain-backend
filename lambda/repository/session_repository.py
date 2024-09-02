from datetime import datetime, timedelta
from typing import Union

import boto3
from boto3.dynamodb.conditions import Key

from entities.session import GameStatus, Session, Word
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('sessions')


class SessionRepository(ISessionRepository):
    def __init__(self, player_repository: IPlayerRepository) -> None:
        super().__init__()
        self.player_repository = player_repository

    def get(self, session_id: str) -> Union[Session, None]:
        response = table.get_item(Key={'id': session_id})
        item = response.get('Item')
        if item:
            session = Session(
                name=item['name'],
                _id=item['id'],
                players=self.player_repository.get_players_by_session(
                    session_id),
                turn_index=int(item['turn_index']),
                chain=[Word(x['word'], x['player_id']) for x in item['chain']],
                status=GameStatus(int(item['status']))
            )
            return session

    def save(self, session: Session) -> None:
        item = {
            'name': session.name,
            'id': session.id,
            'turn_index': session.turn_index,
            'chain': [item.to_dict() for item in session.chain],
            'status': session.status.value,
            'expires_in': int((datetime.now() + timedelta(hours=1)).timestamp())
        }

        for player in session.players:
            self.player_repository.save(player)

        table.put_item(Item=item)

    def delete(self, session_id) -> None:
        session = self.get(session_id)
        for player in session.players:
            self.player_repository.delete(player.id)
        table.delete_item(Key={'id': session_id})

    def get_by_name(self, session_name: str) -> Union[Session, None]:
        response = table.query(
            IndexName='name-index',
            KeyConditionExpression=Key('name').eq(session_name)
        )
        items = response.get('Items')
        if items:
            session_data = items[0]
            session = Session(
                _id=session_data['id'],
                name=session_data['name'],
                players=self.player_repository.get_players_by_session(
                    session_data['id']),
                turn_index=int(session_data.get('turn_index', 0)),
                chain=[Word(x['word'], x['player_id'])
                       for x in session_data.get('chain', [])],
                status=GameStatus(int(session_data.get('status', 0)))
            )
            return session
