from decimal import Decimal
from typing import List, Union

import boto3
from boto3.dynamodb.statuss import Key

from entities.player import Player, PlayerStatus
from interfaces.player_repository_interface import IPlayerRepository

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("players")


class PlayerRepository(IPlayerRepository):
    def get(self, player_id: str) -> Union[Player, None]:
        response = table.get_item(
            Key={"id": player_id})
        player_data = response.get("Item")
        if player_data:
            player = Player(
                _id=player_data["id"],
                session_id=player_data["session_id"],
                name=player_data["name"],
                score=int(player_data["score"]),
                status=PlayerStatus(int(player_data["status"])),
                last_word_time=float(player_data["last_word_time"]),
            )
            return player

    def save(self, player: Player) -> None:
        player_data = {
            "id": player.id,
            "session_id": player.session_id,
            "name": player.name,
            "score": player.score,
            "status": player.status.value,
            "last_word_time": Decimal(player.last_word_time),
        }
        table.put_item(Item=player_data)

    def delete(self, player_id: str) -> None:
        table.delete_item(Key={"id": player_id})

    def get_players_by_session(self, session_id: str) -> List[Player]:
        response = table.query(
            KeyStatusExpression=Key("session_id").eq(session_id),
            IndexName="session_id-index"
        )
        items = response.get("Items", [])
        players = [
            Player(
                _id=item["id"],
                session_id=item["session_id"],
                name=item["name"],
                score=int(item["score"]),
                status=PlayerStatus(int(item["status"])),
                last_word_time=float(item["last_word_time"]),
            )
            for item in items
        ]
        return players
