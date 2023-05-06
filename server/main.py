import json
import traceback
from repository.session_repository import SessionRepository
from game import Game
from utils.http_response import HttpResponse
from entities.RepositoryManager import RepositoryManager


def main(event, context):
  print(json.dumps(event))
  print(context)
  
  session_repository = SessionRepository()
  RepositoryManager.set_repository(session_repository)
  game = Game(session_repository)

  if 'requestContext' not in event: return HttpResponse.BadRequest('requestContext is required')
  
  game.set_connection_id(event['requestContext']['connectionId'])
  
  if 'routeKey' not in event['requestContext']: return HttpResponse.BadRequest('requestContext.routeKey is required')
  
  if event['requestContext']['routeKey'] == '$connect': return HttpResponse.Ok('', {'data': 'Success'})
  if event['requestContext']['routeKey'] == '$disconnect': return game.disconnect()
  
  if 'body' not in event: return HttpResponse.BadRequest('body is required')
  if 'data' not in event['body']: return HttpResponse.BadRequest('body.data is required')
  
  body = json.loads(event['body'])
  
  if not isinstance(body['data'], list): return HttpResponse.BadRequest('body.data should be a list')

  switch = {
    'host': game.host,
    'join': game.join,
    'condition': game.condition,
    'start': game.start,
    'word': game.word,
  }

  try:
    response = switch[body['action']](*body['data'])
    return HttpResponse.Ok(response.action, {'data': response.data})
  except KeyError:
    return HttpResponse.BadRequest('Invalid command!')
  except Exception as e:
    traceback.print_exc()
    return HttpResponse.InternalServerError('Internal error!', str(e))