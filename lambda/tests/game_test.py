import unittest
from unittest.mock import MagicMock, mock_open, patch
from entities.player import Player, PlayerStatus
from entities.repository_manager import RepositoryManager
from entities.session import GameConfig, GameStatus, Session, Word
from messages.messages_pt import ErrorMessage
from responses.action_response import ActionResponse
from utils.errors import GameException
from game import Game, GameData
from utils import wordlist


class TestGame(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 1000
        self.session_repository = MagicMock()
        self.player_repository = MagicMock()
        self.api_gateway = MagicMock()
        RepositoryManager.set_repository(self.session_repository)
        self.game = Game(self.session_repository, self.player_repository, self.api_gateway)

    def test_load_words(self):
        wordlist.clear_cache()
        with patch('builtins.open', mock_open(read_data='casas\npao\n\nlivro\n')):
            self.game.load_words()

        self.assertEqual(self.game.words, frozenset({'casas', 'pao', 'livro'}))
        self.assertEqual(set(self.game.word_list), {'casas', 'pao', 'livro'})
        self.assertEqual(set(self.game.five_letters_words), {'casas', 'livro'})

    def test_load_words_reads_file_once_per_container(self):
        wordlist.clear_cache()
        with patch('builtins.open', mock_open(read_data='casas\nlivro')) as opened:
            self.game.load_words()
            Game(self.session_repository, self.player_repository).load_words()

        opened.assert_called_once()

    def test_set_connection_id(self):
        connection_id = '12345'
        self.game.set_connection_id(connection_id)
        self.assertEqual(self.game.connection_id, connection_id)

    def test_host(self):
        player_name = 'John'
        connection_id = '12345'
        self.game.set_connection_id(connection_id)
        self.game.five_letters_words = ['words']

        with patch('random.choice', return_value='words'):
            response = self.game.host(player_name)

        player: Player = Player(
            player_name, _id=connection_id, session_id=connection_id)
        session: Session = Session('words', _id=connection_id, players=[player])

        expected_response = ActionResponse('host', {'player': player.to_dict(
        ), 'game': GameData(session).to_dict()})

        self.assertEqual(response.action, expected_response.action)
        self.assertEqual(response.data['player']['name'], player_name)
        self.assertEqual(response.data['player']['id'], connection_id)
        self.session_repository.save.assert_called_once()

    def test_join_success(self):
        connection_id = '67890'
        self.game.set_connection_id(connection_id)
        session = Session('words', _id='session_1', status=GameStatus.CREATED)
        self.session_repository.get_by_name.return_value = session

        response = self.game.join('words', 'Jane')

        self.assertEqual(response.action, 'join')
        self.assertEqual(response.data['name'], 'Jane')
        self.assertEqual(response.data['id'], connection_id)
        self.session_repository.save.assert_called_once()

    def test_join_without_session(self):
        connection_id = '12345'
        self.game.set_connection_id(connection_id)
        self.session_repository.get_by_name.side_effect = GameException(ErrorMessage.INEXISTENT_SESSION)

        with self.assertRaises(GameException) as ctx:
            self.game.join('session_id', 'John')
        self.assertEqual(ctx.exception.message, ErrorMessage.INEXISTENT_SESSION.value)

    def test_join_with_started_session(self):
        connection_id = '12345'
        self.game.set_connection_id(connection_id)
        session = Session('session_id', status=GameStatus.STARTED)
        self.session_repository.get_by_name.return_value = session

        with self.assertRaises(GameException) as ctx:
            self.game.join('session_id', 'John')
        self.assertEqual(ctx.exception.message, ErrorMessage.GAME_STARTED.value)

    def _ready_session(self, host_id):
        host = Player('Host', _id=host_id, session_id=host_id, status=PlayerStatus.READY)
        guest = Player('Guest', _id='guest', session_id=host_id, status=PlayerStatus.READY)
        return Session('words', _id=host_id, players=[host, guest])

    def test_start_persists_config_and_sends_it_in_game_data(self):
        self.game.set_connection_id('host_1')
        self.game.word_list = ('palavra',)
        session = self._ready_session('host_1')
        self.session_repository.get.return_value = session

        response = self.game.start('5', 'false')

        self.assertEqual(response.action, 'start')
        self.assertEqual(session.status, GameStatus.STARTED)
        self.assertEqual(session.config, GameConfig(time=5, repetition=False))
        self.assertEqual(GameData(session).to_dict()['config'], {'time': 5, 'repetition': False})
        self.session_repository.save.assert_called_once()

    def test_start_rejects_invalid_config(self):
        self.game.set_connection_id('host_1')
        self.game.word_list = ('palavra',)
        for time, repetition in [('0', 'true'), ('31', 'true'), ('abc', 'true'), ('3', 'maybe')]:
            with self.subTest(time=time, repetition=repetition):
                self.session_repository.get.return_value = self._ready_session('host_1')
                with self.assertRaises(GameException) as ctx:
                    self.game.start(time, repetition)
                self.assertEqual(ctx.exception.code, ErrorMessage.INVALID_CONFIG.name)

    def test_new_session_has_default_config(self):
        session = Session('words')
        self.assertEqual(session.config, GameConfig(time=3, repetition=True))
        self.assertEqual(GameData(session).to_dict()['config'], {'time': 3, 'repetition': True})

    def _playing_session(self, repetition):
        player = Player('John', _id='p1', session_id='s1', status=PlayerStatus.IN_GAME)
        other = Player('Jane', _id='p2', session_id='s1', status=PlayerStatus.IN_GAME)
        session = Session('words', _id='s1', players=[player, other], status=GameStatus.STARTED,
                          chain=[Word('casa', 'p2'), Word('sapo', 'p2')],
                          config=GameConfig(time=3, repetition=repetition))
        self.game.set_connection_id('p1')
        self.player_repository.get.return_value = player
        self.session_repository.get.return_value = session
        self.game.words = frozenset({'casa', 'sapo', 'pote'})
        return session

    def test_repeated_word_rejected_when_repetition_disabled(self):
        self._playing_session(repetition=False)

        with self.assertRaises(GameException) as ctx:
            self.game.word('casa')
        self.assertEqual(ctx.exception.code, ErrorMessage.WORD_ALREADY_IN_GAME.name)

    def test_repeated_word_accepted_when_repetition_enabled(self):
        session = self._playing_session(repetition=True)
        session.chain = [Word('sapo', 'p2'), Word('casa', 'p2')]

        response = self.game.word('sapo')

        self.assertEqual(response.action, 'word')
        self.assertEqual(session.chain[-1].word, 'sapo')

    def test_reconnect_success(self):
        old_conn_id = 'old_123'
        new_conn_id = 'new_456'
        self.game.set_connection_id(new_conn_id)

        old_player = Player('John', _id=old_conn_id, session_id='session_1', status=PlayerStatus.OFFLINE)
        self.player_repository.get.return_value = old_player

        session = Session('words', _id='session_1', players=[old_player], status=GameStatus.STARTED)
        self.session_repository.get.return_value = session

        response = self.game.reconnect(old_conn_id)

        self.assertEqual(response.action, 'reconnect')
        self.assertEqual(response.data['player']['id'], new_conn_id)
        self.assertEqual(response.data['player']['status'], PlayerStatus.IN_GAME)
        self.player_repository.delete.assert_called_once_with(old_conn_id)
        self.session_repository.save.assert_called_once()

    def test_reconnect_inexistent_player(self):
        self.game.set_connection_id('new_456')
        self.player_repository.get.side_effect = GameException(ErrorMessage.INEXISTENT_PLAYER)

        with self.assertRaises(GameException) as ctx:
            self.game.reconnect('old_123')
        self.assertEqual(ctx.exception.message, ErrorMessage.INEXISTENT_PLAYER.value)

    def test_disconnect(self):
        conn_id = '12345'
        self.game.set_connection_id(conn_id)
        player = Player('John', _id=conn_id, session_id='session_1', status=PlayerStatus.IN_GAME)
        self.player_repository.get.return_value = player
        session = Session('words', _id='session_1', players=[player])
        self.session_repository.get.return_value = session

        self.game.disconnect()

        self.assertEqual(player.status, PlayerStatus.OFFLINE)
        self.session_repository.save.assert_called_once()

    def test_end_game(self):
        host_id = 'host_123'
        self.game.set_connection_id(host_id)
        host_player = Player('Host', _id=host_id, session_id='session_1')
        self.player_repository.get.return_value = host_player
        session = Session('words', _id='session_1', players=[host_player], status=GameStatus.STARTED)
        self.session_repository.get.return_value = session

        response = self.game.end_game()

        self.assertEqual(response.action, 'end')
        self.assertEqual(session.status, GameStatus.FINISHED)
        self.session_repository.save.assert_called_once()

    def test_end_game_permission_denied(self):
        host_id = 'host_123'
        other_id = 'other_456'
        self.game.set_connection_id(other_id)
        host_player = Player('Host', _id=host_id, session_id='session_1')
        other_player = Player('Other', _id=other_id, session_id='session_1')
        self.player_repository.get.return_value = other_player
        session = Session('words', _id='session_1', players=[host_player, other_player], status=GameStatus.STARTED)
        self.session_repository.get.return_value = session

        with self.assertRaises(GameException) as ctx:
            self.game.end_game()
        self.assertEqual(ctx.exception.message, ErrorMessage.END_GAME_PERMISSION.value)


if __name__ == '__main__':
    unittest.main()
