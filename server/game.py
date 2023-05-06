import random
from entities.Player import Player, PlayerCondition
from entities.Session import GameStatus, Session
from interfaces.i_session_repository import ISessionRepository
from utils.messages_pt import Error, Message
from utils.calculate_score import calculate_score
from utils.action_response import ActionResponse


class Game:
  def __init__(self, session_repository: ISessionRepository) -> None:  
    self.session_repository: ISessionRepository = session_repository
    self.words = self.load_words()
    self.connection_id = None

  def load_words(self):
    with open('wordlist.txt', 'r', encoding='utf-8') as f:
      return f.read().split('\n')
      
  def set_connection_id(self, connection_id: str):
    self.connection_id = connection_id
    
  def host(self, player_name: str):
    session: Session = Session("_".join(random.sample(self.words, 2)), _id=self.connection_id)
    player: Player = Player(player_name, _id=self.connection_id)
    session.players.append(player)
    session.save()
    
    return ActionResponse('host', {"player_id": player.id, "session_id": session.id, "game_name": session.name, "game_status": int(session.status)})

  def join(self, game_name: str, player_name: str):
    session: Session = self.session_repository.get_by_name(game_name)
    if not session: return self.__error(Error.INEXISTENT_SESSION)
    player: Player = Player(player_name, _id=self.connection_id)
    session.players.append(player)
    session.save()

    return ActionResponse('join', {"player_id": player.id, "session_id": session.id, "game_name": session.name, "game_status": int(session.status)})
  
  def condition(self, player_id: str, player_condition: PlayerCondition, session_id: str):
    session: Session = self.session_repository.get(session_id)
    player: Player = session.find_player(player_id)
    if not player: return self.__error(Error.INEXISTENT_PLAYER)
    player.condition = player_condition
    session.save()

    return ActionResponse('condition', {"players_conditions": [{"player_id": x.id, "player_condition": x.condition} for x in session.players]})

  def start(self, session_id: str):
    session: Session = self.session_repository.get(session_id)
    if not session: return self.__error(Error.INEXISTENT_SESSION)
    if not self.__ready_to_start(session): return self.__error(Error.ALL_PLAYERS_NEED_READY)
    session.status = GameStatus.STARTED
    session.chain.append(random.choice(self.words))
    session.save()
  
    return ActionResponse('start', {
      "game_status": int(session.status), 
      "game_data": {
        "words": session.chain, 
        "players": [{"name": x.name, "player_id": x.id, "points": x.score} for x in session.players],
        "turn": session.turn_index}})
  
  def word(self, session_id: str, player_id: str, word: str):
    session: Session = self.session_repository.get(session_id)
    if not session: return self.__error(Error.INEXISTENT_SESSION)
    if not session.turn_player.id == player_id: return self.__error(Error.INVALID_TURN)
    if word not in self.words: return self.__error(Error.INEXISTENT_WORD)
    if word in session.chain: 
      session.swap_turn()
      return self.__error(Error.WORD_ALREADY_IN_GAME)
    
    score = calculate_score(session.chain[0], word)
    chain_score = calculate_score(word, session.chain[-1])

    if score == 0: return self.__error(Error.NO_POINTS)

    session.turn_player.give_score(chain_score + score)
    session.chain.append(word)

    messages = [Message.POINTS.value.format(score)]
    if chain_score > 0: messages.append(Message.CHAINED.value.format(chain_score))

    return ActionResponse('word', {
      "messages": messages, 
      "game_data": {
        "words": session.chain, 
        "players": [{"name": x.name, "player_id": x.id, "points": x.score} for x in session.players]}})
  
  def set_word_time(self, session_id: str, player_id: str, word_time: float):
    session: Session = self.session_repository.get(session_id)
    if not session: return self.__error(Error.INEXISTENT_SESSION)
    player: Player = session.find_player(player_id)
    if not player: return self.__error(Error.INEXISTENT_PLAYER)

    player.last_word_time = word_time

    session.save()
    
  def disconnect(self):
    self.session_repository.delete(self.connection_id)
  
  def __ready_to_start(self, session: Session):
    return all(x.condition == PlayerCondition.READY for x in session.players)
  
  def __error(self, message: Error):
    return {"error": True, "message": message.value, "code": message.name}