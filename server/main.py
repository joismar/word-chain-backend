from repository.session_repository import SessionRepository
from game import Game
from utils.http_response import HttpResponse


def main(event, context):
  session_respository = SessionRepository()
  game = Game(session_respository)

  if 'requestContext' not in event: return HttpResponse.BadRequest('requestContext is required')
  if 'routeKey' not in event['requestContext']: return HttpResponse.BadRequest('requestContext.routeKey is required')
  if 'body' not in event['requestContext']: return HttpResponse.BadRequest('requestContext.body is required')
  if 'data' not in event['requestContext']['body']: return HttpResponse.BadRequest('requestContext.body.data is required')
  if isinstance(event['requestContext']['body']['data']) != list: return HttpResponse.BadRequest('requestContext.body.data should be a list')

  switch = {
    'host': game.host,
    'join': game.join,
    'condition': game.condition,
    'start': game.start,
    'word': game.word
  }

  try:
    response = switch[event['requestContext']['routeKey']](*event['requestContext']['body']['data'])
    return HttpResponse.Ok({'data': response})
  except KeyError:
    return HttpResponse.BadRequest('Invalid command!')
  except Exception as e:
    return HttpResponse.InternalServerError('Internal error!', str(e))