import os
import unittest

os.environ.setdefault('AWS_DEFAULT_REGION', 'sa-east-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

from entities.player import Player, PlayerColor, PlayerStatus  # noqa: E402
from entities.session import GameConfig, GameStatus, Session, Word  # noqa: E402
from repository.player_repository import PlayerRepository  # noqa: E402
from repository.session_repository import SessionRepository  # noqa: E402
from utils.errors import ConcurrentUpdateError, GameException  # noqa: E402


def create_tables(dynamodb):
    dynamodb.create_table(
        TableName='sessions',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'},
                              {'AttributeName': 'name', 'AttributeType': 'S'}],
        GlobalSecondaryIndexes=[{
            'IndexName': 'name-index',
            'KeySchema': [{'AttributeName': 'name', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'}}],
        BillingMode='PAY_PER_REQUEST')
    dynamodb.create_table(
        TableName='players',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'},
                              {'AttributeName': 'session_id', 'AttributeType': 'S'}],
        GlobalSecondaryIndexes=[{
            'IndexName': 'session_id-index',
            'KeySchema': [{'AttributeName': 'session_id', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'}}],
        BillingMode='PAY_PER_REQUEST')


class TestSessionRepository(unittest.TestCase):
    def setUp(self):
        self.mock = mock_aws()
        self.mock.start()
        dynamodb = boto3.resource('dynamodb')
        create_tables(dynamodb)
        self.players = PlayerRepository(dynamodb.Table('players'))
        self.sessions = SessionRepository(self.players, dynamodb.Table('sessions'))
        self.sessions_table = dynamodb.Table('sessions')

    def tearDown(self):
        self.mock.stop()

    def make_session(self):
        players = [Player(name, _id=pid, session_id='s1', color=PlayerColor.RED)
                   for name, pid in [('Zed', 'z'), ('Ana', 'a'), ('Mia', 'm')]]
        return Session('casas', _id='s1', players=players)

    def test_round_trip_keeps_fields_and_player_order(self):
        session = self.make_session()
        session.start(GameConfig(time=5, repetition=False), 'casa', 1_000)
        session.chain.append(Word('sapo', 'a'))
        self.sessions.save(session)

        loaded = self.sessions.get('s1')

        self.assertEqual([p.id for p in loaded.players], ['z', 'a', 'm'])
        self.assertEqual(loaded.config, GameConfig(time=5, repetition=False))
        self.assertEqual(loaded.status, GameStatus.STARTED)
        self.assertEqual(loaded.started_at, session.started_at)
        self.assertEqual(loaded.ends_at, session.ends_at)
        self.assertEqual(loaded.turn_deadline, session.turn_deadline)
        self.assertEqual([(w.word, w.player_id) for w in loaded.chain],
                         [('casa', None), ('sapo', 'a')])
        self.assertEqual(loaded.players[0].status, PlayerStatus.IN_GAME)
        self.assertEqual(self.sessions.get_by_name('casas').id, 's1')

    def test_save_bumps_version(self):
        session = self.make_session()
        self.sessions.save(session)
        self.assertEqual(session.version, 1)
        self.sessions.save(session)
        self.assertEqual(self.sessions.get('s1').version, 2)

    def test_stale_write_is_rejected(self):
        self.sessions.save(self.make_session())
        first = self.sessions.get('s1')
        second = self.sessions.get('s1')

        first.turn_index = 1
        self.sessions.save(first)
        second.turn_index = 2
        with self.assertRaises(ConcurrentUpdateError):
            self.sessions.save(second)

        self.assertEqual(self.sessions.get('s1').turn_index, 1)

    def test_players_are_not_written_when_the_session_write_conflicts(self):
        self.sessions.save(self.make_session())
        stale = self.sessions.get('s1')
        self.sessions.save(self.sessions.get('s1'))

        stale.players[0].score = 99
        with self.assertRaises(ConcurrentUpdateError):
            self.sessions.save(stale)

        self.assertEqual(self.players.get('z').score, 0)

    def test_creating_over_an_existing_session_conflicts(self):
        self.sessions.save(self.make_session())
        with self.assertRaises(ConcurrentUpdateError):
            self.sessions.save(self.make_session())

    def test_legacy_item_without_version_or_config_loads_with_defaults(self):
        self.sessions_table.put_item(Item={
            'id': 'old', 'name': 'velho', 'turn_index': 0, 'chain': [],
            'status': 0, 'game_mode': 0, 'started_at': None})

        legacy = self.sessions.get('old')
        self.assertEqual(legacy.version, 0)
        self.assertEqual(legacy.config, GameConfig())
        self.sessions.save(legacy)
        self.assertEqual(self.sessions.get('old').version, 1)

    def test_missing_session_raises(self):
        for lookup in (lambda: self.sessions.get('nope'),
                       lambda: self.sessions.get_by_name('nope')):
            with self.assertRaises(GameException) as ctx:
                lookup()
            self.assertEqual(ctx.exception.code, 'INEXISTENT_SESSION')


if __name__ == '__main__':
    unittest.main()
