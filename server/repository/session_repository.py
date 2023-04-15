import json
from entities.Player import Player
from entities.Session import Session
from interfaces.i_session_repository import ISessionRepository


class SessionRepository(ISessionRepository):

  def get_session(self, game_name: str) -> Session:
    with open('sessions.json', 'r') as file:
      file_string = file.read()
      if (len(file_string)):
        sessions = json.loads(file_string)
        session_dict = sessions[game_name]
        session_dict_players = session_dict.pop('players')
        players = list(map(lambda player: Player(**player), session_dict_players))

        return Session(**session_dict, players=players)
  
  def save_session(self, session: Session):
      session_json = session.to_dict()
      
      with open('sessions.json', 'w+') as file:
        sessions = {}
        file_string = file.read()
        if (len(file_string)):
          sessions = json.loads(file_string)
        
        sessions[session.name] = session_json
        file.write(json.dumps(sessions))
        return sessions[session.name]