from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import boto3
from boto3.dynamodb.conditions import Key

from entities.player import Player, PlayerColor, PlayerStatus
from interfaces.player_repository_interface import IPlayerRepository
from messages.messages_pt import ErrorMessage
from utils.errors import GameException

PLAYER_TTL = timedelta(hours=1)


def _player_from_item(item) -> Player:
    color = item.get('color')
    return Player(
        _id=item['id'],
        session_id=item['session_id'],
        name=item['name'],
        score=int(item['score']),
        status=PlayerStatus(int(item['status'])),
        last_word_time=float(item.get('last_word_time', 0)),
        # RED is 0, so test for None rather than truthiness.
        color=PlayerColor(int(color)) if color is not None else None,
    )


class PlayerRepository(IPlayerRepository):
    def __init__(self, table=None) -> None:
        self.table = table or boto3.resource('dynamodb').Table('players')

    def get(self, player_id: str) -> Player:
        item = self.table.get_item(Key={'id': player_id}).get('Item')
        if not item:
            raise GameException(ErrorMessage.INEXISTENT_PLAYER)
        return _player_from_item(item)

    def save(self, player: Player) -> None:
        self.table.put_item(Item={
            'id': player.id,
            'session_id': player.session_id,
            'name': player.name,
            'score': player.score,
            'status': player.status.value,
            'last_word_time': Decimal(str(player.last_word_time)),
            'expires_in': int((datetime.now() + PLAYER_TTL).timestamp()),
            'color': int(player.color.value) if player.color is not None else None,
        })

    def delete(self, player_id: str) -> None:
        self.table.delete_item(Key={'id': player_id})

    def get_players_by_session(self, session_id: str) -> List[Player]:
        response = self.table.query(
            KeyConditionExpression=Key('session_id').eq(session_id),
            IndexName='session_id-index'
        )
        return [_player_from_item(item) for item in response.get('Items', [])]
