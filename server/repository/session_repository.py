import json
from entities.Player import Player
from entities.Session import Session, GameStatus
from interfaces.i_session_repository import ISessionRepository
from boto3.dynamodb.conditions import Key
import boto3


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('sessions')

class SessionRepository(ISessionRepository):
  def get(self, game_name: str) -> Session:
    response = table.get_item(Key={'name': game_name})
    item = response.get('Item')
    if item:
        session = Session(
            name=item['name'],
            _id=item['id'],
            players=item['players'],
            turn_index=item['turn_index'],
            chain=item['chain'],
            status=GameStatus(item['status'])
        )
        return session
  
  def save(self, session: Session):
    item = {
      'name': session.name,
      'id': session.id,
      'players': [player.to_dict() for player in session.players],
      'turn_index': session.turn_index,
      'chain': session.chain,
      'status': session.status.value,
    }
    
    table.put_item(Item=item)
    return session
    
  def delete(self, session_id):
    table.delete_item(Key={'id': session_id})
    
  def get_by_name(self, session_name: str):
    print(session_name)
    response = table.query(
      IndexName='name-index',
      KeyConditionExpression=Key('name').eq(session_name)
    )
    print(response)
    items = response.get('Items')
    if items:
      session_data = items[0]
      players = session_data.get('players', [])
      for player in players: player['_id'] = player.pop('id')
      session = Session(
        _id=session_data['id'],
        name=session_data['name'],
        players=[Player(**player) for player in players],
        turn_index=session_data.get('turn_index', 0),
        chain=session_data.get('chain', []),
        status=GameStatus(session_data.get('status', 'CREATED'))
      )
      return session