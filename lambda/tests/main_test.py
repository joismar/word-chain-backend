import unittest
from unittest.mock import patch, MagicMock
from entities.repository_manager import RepositoryManager
from game import Game
from main import GameApplication
from responses.action_response import ActionResponse
from responses.http_response import HttpResponse


class TestMain(unittest.TestCase):
    def setUp(self):
        self.session_repository = MagicMock()
        self.player_repository = MagicMock()
        RepositoryManager.set_repository(self.session_repository)
        self.app = GameApplication(
            self.session_repository, self.player_repository, None)

    def test_connect_event(self):
        event = {
            'requestContext': {'connectionId': '123', 'routeKey': '$connect'},
        }
        context = {}
        expected_response = HttpResponse.Ok()

        response = self.app.run(event, context)
        self.assertEqual(response, expected_response)

    def test_event_without_body_or_data(self):
        for body in [{}, {'body': '{}'}]:
            event = {'requestContext': {
                'connectionId': '123', 'routeKey': '$default'}, **body}
            context = {}
            response = self.app.run(event, context)
            self.assertEqual(response['statusCode'], 400)

    def test_event_data_should_be_list(self):
        event = {
            'requestContext': {'connectionId': '123', 'routeKey': '$default'},
            'body': '{"data": "str", "action": "host"}'
        }
        context = {}
        response = self.app.run(event, context)
        self.assertEqual(response['statusCode'], 400)

    def test_disconnect_event(self):
        event = {'requestContext': {
            'connectionId': '123', 'routeKey': '$disconnect'}}
        context = {}

        with patch.object(Game, 'disconnect') as mock_disconnect:
            response = self.app.run(event, context)
            mock_disconnect.assert_called_once()
            self.assertEqual(response, HttpResponse.Ok())

    def test_default_events(self):
        for action in ['host', 'join', 'status', 'start', 'word', 'reconnect']:
            with patch.object(Game, action, return_value=ActionResponse(action, {})) as mock_action, \
                 patch.object(Game, 'load_words'):
                event = {
                    'requestContext': {'connectionId': '123', 'routeKey': '$default'},
                    'body': f'{{"data": ["any"], "action": "{action}"}}'
                }
                context = {}
                expected_response = HttpResponse.Ok(action, {'data': {}})

                response = self.app.run(event, context)
                mock_action.assert_called_with('any')
                self.assertEqual(response, expected_response)


if __name__ == '__main__':
    unittest.main()
