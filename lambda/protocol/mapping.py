"""Domain objects -> protocol v2 models."""
from entities.player import Player, PlayerStatus
from entities.session import GameStatus, Session
from protocol import models as wire

PLAYER_STATUS = {
    PlayerStatus.WAITING: 'waiting',
    PlayerStatus.READY: 'ready',
    PlayerStatus.IN_GAME: 'playing',
    PlayerStatus.OFFLINE: 'offline',
}

GAME_STATUS = {
    GameStatus.CREATED: 'lobby',
    GameStatus.STARTED: 'playing',
    GameStatus.FINISHED: 'finished',
}


def player_view(player: Player) -> wire.Player:
    return wire.Player(
        id=player.id,
        name=player.name,
        score=player.score,
        status=PLAYER_STATUS[player.status],
        color=player.color.name.lower() if player.color is not None else None,
    )


def game_state(session: Session, now: int) -> wire.GameState:
    host = session.host
    turn_player = session.turn_player if session.status == GameStatus.STARTED else None
    return wire.GameState(
        name=session.name,
        status=GAME_STATUS[session.status],
        players=[player_view(player) for player in session.players],
        chain=[wire.ChainWord(word=word.word, player_id=word.player_id)
               for word in session.chain],
        host_id=host.id if host else None,
        turn_player_id=turn_player.id if turn_player else None,
        config=wire.GameConfig(time=session.config.time,
                               repetition=session.config.repetition),
        started_at=session.started_at,
        ends_at=session.ends_at,
        turn_deadline=session.turn_deadline,
        server_time=now,
        version=session.version,
    )
