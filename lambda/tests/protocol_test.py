import unittest

from pydantic import ValidationError

from messages.messages_pt import ErrorMessage
from protocol import export_schema
from protocol.models import (AckMessage, AckPayload, ErrorPayload, ErrorReply,
                             StartMessage, WordMessage, client_message_adapter,
                             server_message_adapter, to_wire)


def envelope(type_, payload, **extra):
    return {'v': 2, 'type': type_, 'requestId': 'r1', 'payload': payload, **extra}


class TestClientMessages(unittest.TestCase):
    def test_parses_each_type_by_discriminator(self):
        message = client_message_adapter.validate_python(
            envelope('start', {'config': {'time': 5, 'repetition': False}}))
        self.assertIsInstance(message, StartMessage)
        self.assertEqual(message.payload.config.time, 5)
        self.assertEqual(message.request_id, 'r1')

        message = client_message_adapter.validate_python(envelope('word', {'word': 'casa'}))
        self.assertIsInstance(message, WordMessage)

    def test_accepts_camel_case_payload_fields(self):
        message = client_message_adapter.validate_python(
            envelope('join', {'roomName': 'casas', 'playerName': 'Ana'}))
        self.assertEqual(message.payload.room_name, 'casas')

    def test_rejects_invalid_messages(self):
        invalid = [
            {**envelope('pass', {}), 'v': 1},
            envelope('end', {}),
            envelope('host', {'playerName': ''}),
            envelope('host', {'playerName': 'x' * 21}),
            envelope('host', {'playerName': 'Ana', 'extra': 1}),
            envelope('start', {'config': {'time': 0, 'repetition': True}}),
            envelope('start', {'config': {'time': 31, 'repetition': True}}),
            {'v': 2, 'type': 'pass', 'payload': {}},
            {'action': 'host', 'data': ['Ana']},
        ]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                client_message_adapter.validate_python(raw)


class TestServerMessages(unittest.TestCase):
    def test_serializes_camel_case_envelope(self):
        wire = to_wire(AckMessage(request_id='r1', payload=AckPayload(points=3, chain_points=1)))
        self.assertEqual(wire, {'v': 2, 'type': 'ack', 'requestId': 'r1',
                                'payload': {'points': 3, 'chainPoints': 1}})

    def test_error_codes_come_from_error_messages(self):
        error = ErrorReply(request_id=None, payload=ErrorPayload(
            code=ErrorMessage.INVALID_TURN.name, message=ErrorMessage.INVALID_TURN.value))
        self.assertEqual(to_wire(error)['payload']['code'], 'INVALID_TURN')
        with self.assertRaises(ValidationError):
            ErrorPayload(code='NOT_A_CODE', message='x')

    def test_round_trips_through_adapter(self):
        wire = to_wire(AckMessage(request_id='r1', payload=AckPayload()))
        self.assertIsInstance(server_message_adapter.validate_python(wire), AckMessage)


class TestSchemaFile(unittest.TestCase):
    def test_committed_schema_matches_models(self):
        self.assertEqual(export_schema.main(['--check']), 0,
                         'run: python -m protocol.export_schema')


if __name__ == '__main__':
    unittest.main()
