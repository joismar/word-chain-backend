import unittest
from unittest.mock import MagicMock, mock_open, patch
from entities.player import Player
from entities.repository_manager import RepositoryManager
from entities.session import GameStatus
from responses.action_response import ActionResponse
from game import Game


class TestGame(unittest.TestCase):
    def setUp(self):
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

        with patch('random.sample', return_value=['word1', 'word2']):
            response = self.game.host(player_name)

        player: Player = Player(
            player_name, _id=connection_id, session_id=connection_id)

        expected_response = ActionResponse('host', {'player': player.to_dict(
        ), 'game': {'game_name': 'word1_word2', 'status': GameStatus.CREATED}})

        self.assertEqual(response.data, expected_response.data)
        self.assertEqual(response.action, expected_response.action)

        self.session_repository.save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
