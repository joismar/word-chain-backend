import json
from entities.Player import Player
from entities.Session import Session
from interfaces.i_session_repository import ISessionRepository


class SessionRepository(ISessionRepository):
  def get_session(self, game_name: str) -> Session:
    with open('sessions.json', 'r', encoding='utf-8') as file:
      file_string = file.read()
      if (len(file_string)):
        sessions = json.loads(file_string)
        session_dict = sessions[game_name]
        session_dict_players = session_dict.pop('players')
        players = [Player(**player) for player in session_dict_players]

        return Session(**session_dict, players=players)
  
  def save_session(self, session: Session):
      session_json = session.to_dict()
      
      with open('./sessions.json', 'w+', encoding='utf-8') as file:
        sessions = {}
        file_string = file.read()
        if (len(file_string)):
          sessions = json.loads(file_string)
        
        sessions[session.name] = session_json
        file.write(json.dumps(sessions, indent=2))
        return sessions[session.name]