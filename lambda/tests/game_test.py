import os
import unittest
from unittest.mock import patch

os.environ.setdefault('POWERTOOLS_LOG_LEVEL', 'CRITICAL')

from entities.player import PlayerStatus  # noqa: E402
from entities.session import START_COUNTDOWN_MS, TURN_MS, GameStatus, Word  # noqa: E402
from game import Game  # noqa: E402
from protocol.models import AckMessage, SessionMessage, client_message_adapter  # noqa: E402
from tests.fakes import FakeGateway, FakePlayerRepository, FakeSessionRepository  # noqa: E402
from utils.errors import GameException  # noqa: E402

WORD_LIST = ('casas', 'livro', 'casa', 'sapo', 'pote', 'teto', 'sala', 'lata', 'saco')
WORDS = (frozenset(WORD_LIST), WORD_LIST, ('casas', 'livro'))
T0 = 1_700_000_000_000


def msg(type_, **payload):
    return client_message_adapter.validate_python(
        {'v': 2, 'type': type_, 'requestId': f'req-{type_}', 'payload': payload})


class GameTestCase(unittest.TestCase):
    def setUp(self):
        self.players = FakePlayerRepository()
        self.sessions = FakeSessionRepository(self.players)
        self.gateway = FakeGateway()
        self.now = T0
        self.choice = patch('game.random.choice', side_effect=lambda seq: list(seq)[0])
        self.choice.start()
        self.addCleanup(self.choice.stop)

    def game(self, connection_id):
        return Game(self.sessions, self.players, self.gateway,
                    connection_id=connection_id, now=self.now, words_loader=lambda: WORDS)

    def send(self, connection_id, type_, **payload):
        return self.game(connection_id).handle(msg(type_, **payload))

    def assert_error(self, code, connection_id, type_, **payload):
        with self.assertRaises(GameException) as ctx:
            self.send(connection_id, type_, **payload)
        self.assertEqual(ctx.exception.code, code)

    def reset(self):
        self.sessions.items.clear()
        self.players.items.clear()

    def session(self):
        (session_id,) = self.sessions.items
        return self.sessions.get(session_id)

    def lobby(self, *guests):
        reply = self.send('h', 'host', playerName='Host')
        for guest in guests:
            self.send(guest, 'join', roomName=reply.payload.game.name, playerName=guest.upper())
        return reply.payload.game.name

    def playing(self, *guests, repetition=False):
        self.lobby(*guests)
        for connection_id in ('h', *guests):
            self.send(connection_id, 'ready', ready=True)
        self.send('h', 'start', config={'time': 3, 'repetition': repetition})
        self.now += START_COUNTDOWN_MS
        # The first word is WORD_LIST[0] via the patched random.choice.
        return self.session()


class TestLobby(GameTestCase):
    def test_host_creates_room_and_replies_with_session(self):
        reply = self.send('h', 'host', playerName='  Ana ')

        self.assertIsInstance(reply, SessionMessage)
        self.assertEqual(reply.request_id, 'req-host')
        self.assertEqual(reply.payload.player.name, 'Ana')
        self.assertEqual(reply.payload.player.id, 'h')
        self.assertEqual(reply.payload.game.name, 'casas')
        self.assertEqual(reply.payload.game.host_id, 'h')
        self.assertEqual(reply.payload.game.status, 'lobby')
        self.assertEqual(reply.payload.game.server_time, T0)

    def test_join_normalizes_room_name_and_broadcasts(self):
        self.lobby()

        reply = self.send('g', 'join', roomName=' CASAS ', playerName='Bia')

        self.assertEqual([p.id for p in reply.payload.game.players], ['h', 'g'])
        self.assertEqual([p['name'] for p in self.gateway.last_state('h')['players']],
                         ['Host', 'Bia'])
        self.assertNotEqual(reply.payload.player.color, reply.payload.game.players[0].color)

    def test_join_rejects_started_and_full_rooms(self):
        self.lobby(*[f'g{i}' for i in range(7)])
        self.assert_error('ROOM_FULL', 'late', 'join', roomName='casas', playerName='X')

        self.reset()
        self.playing('g')
        self.assert_error('GAME_STARTED', 'late', 'join', roomName='casas', playerName='X')

    def test_join_unknown_room(self):
        self.assert_error('INEXISTENT_SESSION', 'g', 'join', roomName='nada', playerName='X')

    def test_ready_toggles_status(self):
        self.lobby('g')

        reply = self.send('g', 'ready', ready=True)

        self.assertIsInstance(reply, AckMessage)
        self.assertEqual(self.session().find_player('g').status, PlayerStatus.READY)
        self.send('g', 'ready', ready=False)
        self.assertEqual(self.session().find_player('g').status, PlayerStatus.WAITING)

    def test_only_host_starts_and_everyone_must_be_ready(self):
        self.lobby('g')
        self.send('h', 'ready', ready=True)

        self.assert_error('NOT_HOST', 'g', 'start', config={'time': 3, 'repetition': True})
        self.assert_error('ALL_PLAYERS_NEED_READY', 'h', 'start',
                          config={'time': 3, 'repetition': True})

    def test_start_persists_config_and_deadlines(self):
        session = self.playing('g')

        self.assertEqual(session.status, GameStatus.STARTED)
        self.assertEqual((session.config.time, session.config.repetition), (3, False))
        state = self.gateway.last_state('g')
        self.assertEqual(state['status'], 'playing')
        self.assertEqual(state['config'], {'time': 3, 'repetition': False})
        self.assertEqual(state['startedAt'], T0 + START_COUNTDOWN_MS)
        self.assertEqual(state['turnPlayerId'], 'h')
        self.assertEqual(state['chain'], [{'word': 'casas', 'playerId': None}])


class TestTurns(GameTestCase):
    def test_word_scores_appends_and_passes_turn(self):
        session = self.playing('g')
        session.chain[-1].word = 'casa'
        self.sessions.save(session)

        reply = self.send('h', 'word', word=' SAPO ')

        self.assertEqual((reply.payload.points, reply.payload.chain_points), (2, 0))
        session = self.session()
        self.assertEqual(session.chain[-1].word, 'sapo')
        self.assertEqual(session.chain[-1].player_id, 'h')
        self.assertEqual(session.find_player('h').score, 2)
        self.assertEqual(session.turn_player.id, 'g')
        self.assertEqual(session.turn_deadline, self.now + TURN_MS)

    def test_word_strips_accents(self):
        session = self.playing('g')
        session.chain[-1].word = 'sapo'
        self.sessions.save(session)

        self.send('h', 'word', word='Pôte')

        self.assertEqual(self.session().chain[-1].word, 'pote')

    def test_word_errors(self):
        self.playing('g')
        self.assert_error('INVALID_TURN', 'g', 'word', word='sala')
        self.assert_error('INEXISTENT_WORD', 'h', 'word', word='xyzw')
        self.assert_error('NO_POINTS', 'h', 'word', word='livro')

    def test_cannot_play_during_countdown_or_before_start(self):
        self.lobby('g')
        self.assert_error('GAME_NOT_STARTED', 'h', 'word', word='sala')

        self.reset()
        self.playing('g')
        self.now -= 1
        self.assert_error('GAME_NOT_STARTED', 'h', 'word', word='sala')

    def test_repeated_word_passes_turn_when_repetition_is_off(self):
        self.playing('g')

        self.assert_error('WORD_ALREADY_IN_GAME', 'h', 'word', word='casas')

        self.assertEqual(self.session().turn_player.id, 'g')

    def test_repeated_word_allowed_when_repetition_is_on(self):
        session = self.playing('g', repetition=True)
        session.chain += [Word('saco', 'g'), Word('casa', 'g')]
        self.sessions.save(session)

        self.send('h', 'word', word='saco')

        self.assertEqual(self.session().chain[-1].word, 'saco')

    def test_pass_hands_turn_over(self):
        self.playing('g')

        self.send('h', 'pass')

        self.assertEqual(self.session().turn_player.id, 'g')


class TestDeadlines(GameTestCase):
    def test_any_message_applies_an_expired_turn_first(self):
        session = self.playing('g')
        self.now = session.turn_deadline

        # h's turn expired, so h's word arrives too late.
        self.assert_error('INVALID_TURN', 'h', 'word', word='sala')

        self.assertEqual(self.session().turn_player.id, 'g')
        self.assertEqual(self.gateway.last_state('g')['turnPlayerId'], 'g')

    def test_timeout_is_rejected_before_the_server_deadline(self):
        session = self.playing('g')
        self.now = session.turn_deadline - 1

        self.assert_error('DEADLINE_NOT_REACHED', 'g', 'timeout')
        self.assertEqual(self.session().turn_player.id, 'h')

    def test_timeout_after_the_deadline_passes_the_turn(self):
        session = self.playing('g')
        self.now = session.turn_deadline

        reply = self.send('g', 'timeout')

        self.assertIsInstance(reply, AckMessage)
        self.assertEqual(self.session().turn_player.id, 'g')

    def test_timeout_after_ends_at_finishes_the_match(self):
        session = self.playing('g')
        self.now = session.ends_at

        self.send('h', 'timeout')

        self.assertEqual(self.session().status, GameStatus.FINISHED)
        self.assertEqual(self.gateway.last_state('g')['status'], 'finished')
        self.assert_error('GAME_FINISHED', 'h', 'word', word='sala')


class TestConnections(GameTestCase):
    def test_reconnect_moves_player_to_new_connection(self):
        self.playing('g')

        reply = self.send('g2', 'reconnect', playerId='g')

        self.assertEqual(reply.payload.player.id, 'g2')
        self.assertEqual(reply.payload.player.status, 'playing')
        self.assertEqual([p.id for p in self.session().players], ['h', 'g2'])
        self.assertNotIn('g', self.players.items)

    def test_reconnect_unknown_player(self):
        self.assert_error('INEXISTENT_PLAYER', 'x', 'reconnect', playerId='ghost')

    def test_disconnect_marks_offline_and_tells_the_others(self):
        self.playing('g')

        self.game('g').disconnect()

        self.assertEqual(self.session().find_player('g').status, PlayerStatus.OFFLINE)
        self.assertEqual(self.gateway.last_state('h')['players'][1]['status'], 'offline')

    def test_disconnect_of_unknown_connection_is_ignored(self):
        self.game('nobody').disconnect()

    def test_gone_connections_are_marked_offline(self):
        self.playing('g', 'k')
        self.gateway.gone.add('k')

        self.send('h', 'pass')

        self.assertEqual(self.session().find_player('k').status, PlayerStatus.OFFLINE)
        self.assertEqual(self.gateway.last_state('h')['players'][2]['status'], 'offline')

    def test_offline_players_get_no_broadcasts(self):
        self.playing('g')
        self.game('g').disconnect()
        sent_before = len(self.gateway.messages_to('g'))

        self.send('h', 'pass')

        self.assertEqual(len(self.gateway.messages_to('g')), sent_before)


if __name__ == '__main__':
    unittest.main()
