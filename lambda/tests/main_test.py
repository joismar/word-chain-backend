import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('POWERTOOLS_LOG_LEVEL', 'CRITICAL')
os.environ.setdefault('POWERTOOLS_TRACE_DISABLED', '1')

import main as handler_module  # noqa: E402
from game import Game  # noqa: E402
from main import MAX_ATTEMPTS, GameApplication  # noqa: E402
from tests.fakes import FakeGateway, FakePlayerRepository, FakeSessionRepository  # noqa: E402
from utils.errors import ConcurrentUpdateError  # noqa: E402

WORD_LIST = ('casas', 'casa', 'sapo')
WORDS = (frozenset(WORD_LIST), WORD_LIST, ('casas',))


def event(route='$default', body=None, connection_id='c1'):
    e = {'requestContext': {'connectionId': connection_id, 'routeKey': route}}
    if body is not None:
        e['body'] = body if isinstance(body, str) else json.dumps(body)
    return e


def host_body(request_id='r1'):
    return {'v': 2, 'type': 'host', 'requestId': request_id, 'payload': {'playerName': 'Ana'}}


class TestGameApplication(unittest.TestCase):
    def setUp(self):
        self.players = FakePlayerRepository()
        self.sessions = FakeSessionRepository(self.players)
        self.gateway = FakeGateway()
        self.app = GameApplication(self.sessions, self.players, self.gateway,
                                   clock=lambda: 1_000, words_loader=lambda: WORDS)

    def reply(self, connection_id='c1'):
        (message,) = [m for m in self.gateway.messages_to(connection_id)
                      if m['type'] != 'game_state']
        return message

    def assert_error_reply(self, code, request_id=None):
        message = self.reply()
        self.assertEqual(message['type'], 'error')
        self.assertEqual(message['v'], 2)
        self.assertEqual(message['requestId'], request_id)
        self.assertEqual(message['payload']['code'], code)
        self.assertTrue(message['payload']['message'])

    def test_connect_is_accepted(self):
        self.assertEqual(self.app.run(event('$connect')), {'statusCode': 200})
        self.assertEqual(self.gateway.sent, [])

    def test_disconnect_marks_player_offline(self):
        with patch.object(Game, 'disconnect') as disconnect:
            self.assertEqual(self.app.run(event('$disconnect')), {'statusCode': 200})
        disconnect.assert_called_once()

    def test_valid_message_is_answered_through_the_gateway(self):
        response = self.app.run(event(body=host_body()))

        self.assertEqual(response, {'statusCode': 200})
        message = self.reply()
        self.assertEqual(message['type'], 'session')
        self.assertEqual(message['requestId'], 'r1')
        self.assertEqual(message['payload']['player']['name'], 'Ana')

    def test_invalid_json(self):
        self.app.run(event(body='{not json'))
        self.assert_error_reply('INVALID_MESSAGE')

    def test_invalid_payload_keeps_the_request_id(self):
        self.app.run(event(body={**host_body('r9'), 'payload': {}}))
        self.assert_error_reply('INVALID_MESSAGE', 'r9')

    def test_v1_message_gets_unsupported_version(self):
        self.app.run(event(body={'action': 'host', 'data': ['Ana']}))
        self.assert_error_reply('UNSUPPORTED_VERSION')

    def test_game_errors_are_sent_by_code(self):
        self.app.run(event(body={'v': 2, 'type': 'pass', 'requestId': 'r2', 'payload': {}}))
        self.assert_error_reply('INEXISTENT_PLAYER', 'r2')

    def test_concurrent_update_is_retried(self):
        self.sessions.conflicts_to_raise = MAX_ATTEMPTS - 1

        self.app.run(event(body=host_body()))

        self.assertEqual(self.reply()['type'], 'session')
        self.assertEqual(self.sessions.saves, 1)

    def test_concurrent_update_gives_up_after_max_attempts(self):
        self.sessions.conflicts_to_raise = MAX_ATTEMPTS

        self.app.run(event(body=host_body()))

        self.assert_error_reply('CONCURRENT_UPDATE', 'r1')

    def test_unexpected_errors_become_internal_error(self):
        with patch.object(Game, 'handle', side_effect=RuntimeError('boom')):
            self.app.run(event(body=host_body()))
        self.assert_error_reply('INTERNAL_ERROR', 'r1')

    def test_disconnect_is_retried_on_conflict(self):
        with patch.object(Game, 'disconnect',
                          side_effect=[ConcurrentUpdateError('s'), None]) as disconnect:
            self.app.run(event('$disconnect'))
        self.assertEqual(disconnect.call_count, 2)


class FakeLambdaContext:
    function_name = 'word-chain'
    memory_limit_in_mb = 128
    invoked_function_arn = 'arn:aws:lambda:sa-east-1:000000000000:function:word-chain'
    aws_request_id = 'aws-req'


class TestHandler(unittest.TestCase):
    def test_lambda_entry_point_runs_through_powertools_decorators(self):
        players = FakePlayerRepository()
        gateway = FakeGateway()
        app = GameApplication(FakeSessionRepository(players), players, gateway,
                              words_loader=lambda: WORDS)
        with patch.object(handler_module, '_application', app):
            response = handler_module.main(event(body=host_body()), FakeLambdaContext())

        self.assertEqual(response, {'statusCode': 200})
        self.assertEqual(gateway.messages_to('c1')[0]['type'], 'session')


if __name__ == '__main__':
    unittest.main()
