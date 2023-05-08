from typing import List
from entities.player import Player


class IPlayerRepository:
    def get(self, player_id: str) -> Player:
        pass

    def save(self, player: Player) -> None:
        pass

    def delete(self, player_id: str) -> None:
        pass

    def get_players_by_session(self, session_id: str) -> List[Player]:
        pass
