import unittest
from unittest.mock import MagicMock, mock_open, patch
from entities.player import Player
from entities.repository_manager import RepositoryManager
from entities.session import Session
from messages.messages_pt import Error
from responses.action_response import ActionResponse
from game import Game, GameData


class TestGame(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 1000
        self.session_repository = MagicMock()
        self.player_repository = MagicMock()
        RepositoryManager.set_repository(self.session_repository)
        self.game = Game(self.session_repository, self.player_repository)

    def test_load_words(self):
        with patch('builtins.open', mock_open(read_data='word1\nword2\nword3')):
            self.game.load_words()

        self.assertEqual(self.game.words, ['word1', 'word2', 'word3'])

    def test_set_connection_id(self):
        connection_id = "12345"
        self.game.set_connection_id(connection_id)
        self.assertEqual(self.game.connection_id, connection_id)

    def test_host(self):
        player_name = "John"
        connection_id = "12345"
        self.game.set_connection_id(connection_id)

        with patch('random.choice', return_value='word'):
            response = self.game.host(player_name)

        player: Player = Player(
            player_name, _id=connection_id, session_id=connection_id)
        session: Session = Session('word', _id=connection_id, players=[player])

        expected_response = ActionResponse('host', {'player': player.to_dict(
        ), 'game': GameData(session).to_dict()})

        self.assertEqual(response.data, expected_response.data)
        self.assertEqual(response.action, expected_response.action)

        self.session_repository.save.assert_called_once()

    def test_join_without_session(self):
        connection_id = "12345"
        self.game.set_connection_id(connection_id)
        self.session_repository.get_by_name.return_value = None

        response = self.game.join("session_id", "John")

        expected_response = ActionResponse(
            "join",
            {"error": True, "message": Error.INEXISTENT_SESSION.value, "code": Error.INEXISTENT_SESSION.name})

        self.assertEqual(response.data, expected_response.data)
        self.assertEqual(response.action, expected_response.action)

    def test_join_with_started_session(self):
        connection_id = "12345"
        self.game.set_connection_id(connection_id)
        session = Session("session_id", status=1)
        self.session_repository.get_by_name.return_value = session

        response = self.game.join("session_id", "John")

        expected_response = ActionResponse(
            "join",
            {"error": True, "message": Error.GAME_STARTED.value, "code": Error.GAME_STARTED.name})

        self.assertEqual(response.data, expected_response.data)
        self.assertEqual(response.action, expected_response.action)


if __name__ == '__main__':
    unittest.main()
