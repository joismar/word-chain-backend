import json
import os
import traceback
from api_gateway_service import ApiGatewayService
from entities.repository_manager import RepositoryManager
from game import Game
from responses.action_response import ActionResponse
from responses.http_response import HttpResponse
from utils.errors import GameException


class GameApplication:
    def __init__(self, session_repository, player_repository,
                 api_gateway_client):
        self.session_repository = session_repository
        self.player_repository = player_repository
        self.api_gateway_client = api_gateway_client

    def run(self, event, context):
        print(json.dumps(event))
        print(context)

        body = None
        action = None
        if 'body' in event:
            body = json.loads(event['body'])
            if 'action' in body:
                action = body['action']

        try:
            game = Game(self.session_repository,
                        self.player_repository, self.api_gateway_client)
            game.set_connection_id(event['requestContext']['connectionId'])

            if event['requestContext']['routeKey'] == '$connect':
                return HttpResponse.Ok()

            if event['requestContext']['routeKey'] == '$disconnect':
                return game.disconnect()

            if (not body) or ('data' not in body):
                raise KeyError('body or body.data is missing')

            if not action:
                raise KeyError('action is missing')

            if not isinstance(body['data'], list):
                raise KeyError('body.data should be a list')

            for body_data in body['data']:
                if len(body_data) == 0:
                    raise KeyError('body.data should not be empty')

            game.load_words()

            switch = {
                'host': game.host,
                'join': game.join,
                'status': game.status,
                'start': game.start,
                'word': game.word,
                'reconnect': game.reconnect,
                'pass': game.pass_turn,
                'end': game.end_game,
            }

            response = switch[action](*body['data'])
            return HttpResponse.Ok(response.action, {'data': response.data})
        except (KeyError, ValueError, GameException) as e:
            return HttpResponse.BadRequest(e, action)
        except Exception as e:
            traceback.print_exc()
            return HttpResponse.InternalServerError(e)


def main(event, context):
    from repository.player_repository import PlayerRepository
    from repository.session_repository import SessionRepository

    player_repository = PlayerRepository()
    session_repository = SessionRepository(player_repository)
    RepositoryManager.set_repository(session_repository)
    endpoint_url = os.environ.get('API_GATEWAY_URL')
    api_gateway_client = ApiGatewayService(endpoint_url).client

    app = GameApplication(session_repository,
                          player_repository, api_gateway_client)

    return app.run(event, context)
