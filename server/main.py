import json
import os
import traceback

from api_gateway_service import ApiGatewayService
from entities.repository_manager import RepositoryManager
from game import Game
from repository.player_repository import PlayerRepository
from repository.session_repository import SessionRepository
from responses.http_response import HttpResponse


def main(event, context):
    print(json.dumps(event))
    print(context)

    try:
        player_repository = PlayerRepository()
        session_repository = SessionRepository(player_repository)
        RepositoryManager.set_repository(session_repository)
        endpoint_url = os.environ.get('API_GATEWAY_URL')
        api_gateway_client = ApiGatewayService(endpoint_url).client
        game = Game(session_repository, player_repository, api_gateway_client)
        game.set_connection_id(event['requestContext']['connectionId'])

        if event['requestContext']['routeKey'] == '$connect':
            return HttpResponse.Ok()

        if event['requestContext']['routeKey'] == '$disconnect':
            return game.disconnect()

        if ('body' not in event) or ('data' not in json.loads(event['body'])):
            return HttpResponse.BadRequest('body or body.data is missing')

        body = json.loads(event['body'])

        if not isinstance(body['data'], list):
            return HttpResponse.BadRequest('body.data should be a list')

        game.load_words()

        switch = {
            'host': game.host,
            'join': game.join,
            'status': game.status,
            'start': game.start,
            'word': game.word,
        }

        response = switch[body['action']](*body['data'])
        return HttpResponse.Ok(response.action, {'data': response.data})
    except (KeyError, ValueError) as e:
        return HttpResponse.BadRequest('Data validation error!', str(e))
    except Exception as e:
        traceback.print_exc()
        return HttpResponse.InternalServerError('Internal error!', str(e))
