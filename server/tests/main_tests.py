import unittest
from unittest.mock import patch
from game import Game
from main import main
from responses.action_response import ActionResponse
from responses.http_response import HttpResponse


class TestMain(unittest.TestCase):
    def test_connect_event(self):
        event = {
            'requestContext': {'connectionId': '123', 'routeKey': '$connect'},
        }
        context = {}

        expected_response = HttpResponse.Ok()
        response = main(event, context)
        self.assertEqual(response, expected_response)

    def test_event_without_body_or_data(self):
        for body in [{}, {'body': '{}'}]:
            event = {
                'requestContext': {'connectionId': '123', 'routeKey': '$default'},
                **body
            }
            context = {}

            expected_response = HttpResponse.BadRequest('body or body.data is missing')
            response = main(event, context)
            self.assertEqual(response, expected_response)

    def test_event_data_should_be_list(self):
        event = {
            'requestContext': {'connectionId': '123', 'routeKey': '$default'},
            'body': '{"data": "str"}'
        }
        context = {}

        expected_response = HttpResponse.BadRequest('body.data should be a list')
        response = main(event, context)
        self.assertEqual(response, expected_response)


    def test_disconnect_event(self):
        event = {
            'requestContext': {'connectionId': '123', 'routeKey': '$disconnect'}
        }
        context = {}
        expected_response = None

        @patch('main.PlayerRepository')
        @patch('main.SessionRepository')
        @patch('main.ApiGatewayService')
        def test(*_):
            with patch.object(Game, 'disconnect', return_value=expected_response) as mock_disconnect:
                response = main(event, context)
                mock_disconnect.assert_called_once()
                self.assertEqual(response, expected_response)

        test()

    def test_default_events(self):
        @patch('main.PlayerRepository')
        @patch('main.SessionRepository')
        @patch('main.ApiGatewayService')
        def test(*_):
            for action in ['host', 'join', 'condition', 'start', 'word']:
                with patch.object(Game, action, return_value=ActionResponse(action, {})) as mock_action:
                    event = {
                        'requestContext': {'connectionId': '123', 'routeKey': '$default'},
                        'body': f'{{"data": ["any"], "action": "{action}"}}'
                    }
                    context = {}
                    expected_response = HttpResponse.Ok(action, {'data': {}})
                    response = main(event, context)
                    mock_action.assert_called_with("any")
                    self.assertEqual(response, expected_response)

        test()


if __name__ == '__main__':
    unittest.main()
