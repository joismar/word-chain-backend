import random
from entities.Player import Player, PlayerCondition
from entities.Session import GameStatus, Session
from interfaces.i_session_repository import ISessionRepository
from repository.session_repository import SessionRepository


class Game:
  def __init__(self, session_repository: ISessionRepository) -> None:
    self.session_repository: ISessionRepository = session_repository
    self.words = self.load_words()

  def load_words(self):
    with open('server/wordlist.txt', 'r', encoding='utf-8') as f:
      return f.read().split('\n')
    
  def host(self, player_name: str):
    session: Session = Session("_".join(random.sample(self.words, 2)))
    player: Player = Player(player_name)
    session.players.append(player)
    self.session_repository.save_session(session)
    
    return {"player_id": player.id, "session_id": session.id, "game_name": session.name, "game_status": int(session.status)}

  def join(self, game_name: str, player_name: str):
    session: Session = self.session_repository.get_session(game_name)
    if not session: return {"error": True, "message": "Session doesn't exists."}
    player: Player = Player(player_name)
    session.players.append(player)
    self.session_repository.save_session(session)

    return {"player_id": player.id, "session_id": session.id, "game_name": session.name, "game_status": int(session.status)}
  
  def condition(self, player_id: str, player_condition: PlayerCondition, game_name: str):
    session: Session = self.session_repository.get_session(game_name)
    player: Player = session.find_player(player_id)
    if not player: return {"error": True, "message": "Player doesn't exists."}
    player.condition = player_condition
    self.session_repository.save_session(session)

    return {"players_conditions": list(map(lambda x: {"player_id": x.id, "player_condition": x.condition}, session.players))}

  def start(self, game_name: str):
    session: Session = self.session_repository.get_session(game_name)
    if not session: return {"error": True, "message": "Session doesn't exists."}
    if not self.__ready_to_start__(session): return {"error": True, "message": "All players need to be ready."}
    session.status = GameStatus.STARTED
    self.session_repository.save_session(session)
  
    return {
      "game_status": int(session.status), "game_data": {
        "words": random.sample(self.words, 1), 
        "players": list(map(lambda x: {"name": x.name, "player_id": x.id, "points": x.score}, session.players))}}
  
  def __ready_to_start__(self, session: Session):
    return all(map(lambda x: x.condition == PlayerCondition.READY, session.players))


if __name__ == '__main__':
    session_respository = SessionRepository()
    game = Game(session_respository)
    host_game_data = game.host('lala')
    print(host_game_data)
    lili_game_data = game.join(host_game_data["game_name"], 'lili')
    print(lili_game_data)
    lulu_game_data = game.join(host_game_data["game_name"], 'lulu')
    print(lulu_game_data)
    print(game.condition(lili_game_data["player_id"], 1, host_game_data["game_name"]))
    print(game.condition(lulu_game_data["player_id"], 1, host_game_data["game_name"]))
    print(game.condition(host_game_data["player_id"], 1, host_game_data["game_name"]))
    print(game.start(host_game_data["game_name"]))