import json
import unittest
from unittest.mock import MagicMock

from api_gateway_service import ConnectionGateway


class GoneException(Exception):
    pass


def fake_client(gone=()):
    client = MagicMock()
    client.exceptions.GoneException = GoneException

    def post_to_connection(Data, ConnectionId):
        if ConnectionId in gone:
            raise GoneException(ConnectionId)
    client.post_to_connection.side_effect = post_to_connection
    return client


class TestConnectionGateway(unittest.TestCase):
    def test_broadcast_sends_to_every_connection_and_reports_gone_ones(self):
        client = fake_client(gone={'b'})
        gateway = ConnectionGateway(client)

        gone = gateway.broadcast(['a', 'b', 'c'], {'type': 'game_state'})

        self.assertEqual(gone, ['b'])
        sent_to = sorted(call.kwargs['ConnectionId']
                         for call in client.post_to_connection.call_args_list)
        self.assertEqual(sent_to, ['a', 'b', 'c'])
        data = client.post_to_connection.call_args_list[0].kwargs['Data']
        self.assertEqual(json.loads(data), {'type': 'game_state'})

    def test_other_errors_do_not_count_as_gone(self):
        client = fake_client()
        client.post_to_connection.side_effect = RuntimeError('throttled')

        self.assertEqual(ConnectionGateway(client).broadcast(['a'], {}), [])

    def test_send_returns_false_when_gone(self):
        gateway = ConnectionGateway(fake_client(gone={'a'}))
        self.assertFalse(gateway.send('a', {}))
        self.assertTrue(gateway.send('b', {}))

    def test_broadcast_to_nobody(self):
        client = fake_client()
        self.assertEqual(ConnectionGateway(client).broadcast([], {}), [])
        client.post_to_connection.assert_not_called()


if __name__ == '__main__':
    unittest.main()
