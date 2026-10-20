import unittest

from entities.player import Player, PlayerStatus
from entities.session import (START_COUNTDOWN_MS, TURN_MS, GameConfig,
                              GameStatus, Session)

NOW = 1_000_000


def make_session(*statuses):
    players = [Player(f'P{i}', _id=f'p{i}', status=status)
               for i, status in enumerate(statuses)]
    return Session('casas', _id='s1', players=players)


def started_session(*statuses, minutes=3):
    session = make_session(*statuses)
    session.start(GameConfig(time=minutes, repetition=False), 'casa', NOW)
    return session


class TestStart(unittest.TestCase):
    def test_sets_deadlines_after_countdown(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY, minutes=5)

        self.assertEqual(session.status, GameStatus.STARTED)
        self.assertEqual(session.started_at, NOW + START_COUNTDOWN_MS)
        self.assertEqual(session.ends_at, session.started_at + 5 * 60_000)
        self.assertEqual(session.turn_deadline, session.started_at + TURN_MS)
        self.assertEqual(session.turn_player.id, 'p0')
        self.assertEqual([w.word for w in session.chain], ['casa'])
        self.assertIsNone(session.chain[0].player_id)
        self.assertTrue(all(p.status == PlayerStatus.IN_GAME for p in session.players))

    def test_single_player_has_no_turn_timer(self):
        session = started_session(PlayerStatus.READY)
        self.assertIsNone(session.turn_deadline)


class TestDeadlines(unittest.TestCase):
    def test_nothing_changes_before_a_deadline(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY)
        self.assertFalse(session.apply_deadlines(session.turn_deadline - 1))
        self.assertEqual(session.turn_player.id, 'p0')

    def test_expired_turn_passes_to_next_player_from_the_old_deadline(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY)
        deadline = session.turn_deadline

        self.assertTrue(session.apply_deadlines(deadline + 10))

        self.assertEqual(session.turn_player.id, 'p1')
        self.assertEqual(session.turn_deadline, deadline + TURN_MS)

    def test_several_expired_turns_are_all_applied(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY, PlayerStatus.READY)
        deadline = session.turn_deadline

        session.apply_deadlines(deadline + 2 * TURN_MS)

        self.assertEqual(session.turn_player.id, 'p0')
        self.assertEqual(session.turn_deadline, deadline + 3 * TURN_MS)

    def test_offline_players_are_skipped(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY, PlayerStatus.READY)
        session.players[1].status = PlayerStatus.OFFLINE

        session.apply_deadlines(session.turn_deadline)

        self.assertEqual(session.turn_player.id, 'p2')

    def test_turn_timer_stops_when_one_player_is_left(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY)
        session.players[1].status = PlayerStatus.OFFLINE

        session.apply_deadlines(session.turn_deadline)

        self.assertEqual(session.turn_player.id, 'p0')
        self.assertIsNone(session.turn_deadline)

    def test_all_players_offline_does_not_loop_forever(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY)
        for player in session.players:
            player.status = PlayerStatus.OFFLINE

        session.advance_turn(NOW)

        self.assertIsNone(session.turn_deadline)

    def test_match_ends_at_ends_at(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY)

        self.assertTrue(session.apply_deadlines(session.ends_at))

        self.assertEqual(session.status, GameStatus.FINISHED)
        self.assertIsNone(session.turn_deadline)

    def test_deadlines_only_apply_while_playing(self):
        session = make_session(PlayerStatus.READY)
        self.assertFalse(session.apply_deadlines(NOW * 10))


class TestAdvanceTurn(unittest.TestCase):
    def test_resets_turn_deadline_from_now(self):
        session = started_session(PlayerStatus.READY, PlayerStatus.READY)

        session.advance_turn(NOW + 7)

        self.assertEqual(session.turn_player.id, 'p1')
        self.assertEqual(session.turn_deadline, NOW + 7 + TURN_MS)


class TestPlayers(unittest.TestCase):
    def test_host_is_first_player(self):
        session = make_session(PlayerStatus.READY, PlayerStatus.READY)
        self.assertEqual(session.host.id, 'p0')
        self.assertIsNone(Session('casas').host)


if __name__ == '__main__':
    unittest.main()
