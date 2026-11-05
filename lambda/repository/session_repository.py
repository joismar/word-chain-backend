import os
from datetime import datetime, timedelta
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from entities.session import GameConfig, GameStatus, Session, Word
from interfaces.player_repository_interface import IPlayerRepository
from interfaces.session_repository_interface import ISessionRepository
from messages.messages_pt import ErrorMessage
from utils.errors import ConcurrentUpdateError, GameException

SESSION_TTL = timedelta(hours=1)


def _optional_int(value) -> Optional[int]:
    return None if value is None else int(value)


def _config_from_item(item) -> GameConfig:
    # Sessions written before config existed fall back to the defaults.
    config = item.get('config')
    if not config:
        return GameConfig()
    return GameConfig(time=int(config['time']), repetition=bool(config['repetition']))


class SessionRepository(ISessionRepository):
    def __init__(self, player_repository: IPlayerRepository, table=None) -> None:
        super().__init__()
        self.player_repository = player_repository
        self.table = table or boto3.resource('dynamodb').Table(
            os.environ.get('SESSIONS_TABLE', 'sessions'))

    def get(self, session_id: str) -> Session:
        item = self.table.get_item(Key={'id': session_id}).get('Item')
        if not item:
            raise GameException(ErrorMessage.INEXISTENT_SESSION)
        return self.__from_item(item)

    def get_by_name(self, session_name: str) -> Session:
        response = self.table.query(
            IndexName='name-index',
            KeyConditionExpression=Key('name').eq(session_name)
        )
        items = response.get('Items')
        if not items:
            raise GameException(ErrorMessage.INEXISTENT_SESSION)
        return self.__from_item(items[0])

    def save(self, session: Session) -> None:
        """Conditional write on version; players are written only if it succeeds.

        Raises ConcurrentUpdateError when someone else saved this session
        after we read it.
        """
        expected = session.version
        item = {
            'id': session.id,
            'name': session.name,
            'player_ids': [player.id for player in session.players],
            'turn_index': session.turn_index,
            'chain': [word.to_dict() for word in session.chain],
            'status': session.status.value,
            'config': session.config.to_dict(),
            'started_at': session.started_at,
            'ends_at': session.ends_at,
            'turn_deadline': session.turn_deadline,
            'version': expected + 1,
            'expires_in': int((datetime.now() + SESSION_TTL).timestamp()),
        }

        if expected == 0:
            # New session, or one written before versioning existed.
            condition = {'ConditionExpression': 'attribute_not_exists(version)'}
        else:
            condition = {
                'ConditionExpression': 'version = :expected',
                'ExpressionAttributeValues': {':expected': expected},
            }

        try:
            self.table.put_item(Item=item, **condition)
        except ClientError as error:
            if error.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise ConcurrentUpdateError(session.id) from error
            raise

        session.version = expected + 1
        for player in session.players:
            self.player_repository.save(player)

    def delete(self, session_id) -> None:
        session = self.get(session_id)
        for player in session.players:
            self.player_repository.delete(player.id)
        self.table.delete_item(Key={'id': session_id})

    def __from_item(self, item) -> Session:
        players = self.player_repository.get_players_by_session(item['id'])
        # The players index has no order; the session keeps the turn order.
        order = {player_id: index for index, player_id in enumerate(item.get('player_ids', []))}
        players.sort(key=lambda player: order.get(player.id, len(order)))

        return Session(
            _id=item['id'],
            name=item['name'],
            players=players,
            turn_index=int(item.get('turn_index', 0)),
            chain=[Word(x['word'], x.get('player_id')) for x in item.get('chain', [])],
            status=GameStatus(int(item.get('status', 0))),
            config=_config_from_item(item),
            started_at=_optional_int(item.get('started_at')),
            ends_at=_optional_int(item.get('ends_at')),
            turn_deadline=_optional_int(item.get('turn_deadline')),
            version=int(item.get('version', 0)),
        )
