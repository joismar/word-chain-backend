import json
import os
import traceback
from api_gateway_service import ApiGatewayService
from entities.repository_manager import RepositoryManager
from game import Game
from responses.action_response import ActionResponse
from responses.http_response import HttpResponse


class GameApplication:
    def __init__(self, session_repository, player_repository,
                 api_gateway_client):
        self.session_repository = session_repository
        self.player_repository = player_repository
        self.api_gateway_client = api_gateway_client

    def run(self, event, context):
        print(json.dumps(event))
        print(context)

        try:
            game = Game(self.session_repository,
                        self.player_repository, self.api_gateway_client)
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

            for body_data in body['data']:
                if len(body_data) == 0:
                    return HttpResponse.BadRequest('body.data should not be empty')

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

            response = switch[body['action']](*body['data'])
            return HttpResponse.Ok(response.action, {'data': response.data})
        except (KeyError, ValueError) as e:
            if body['action']:
                return HttpResponse.BadRequest('Internal error!', str(e), body['action'])
            return HttpResponse.BadRequest('Data validation error!', str(e))
        except Exception as e:
            traceback.print_exc()
            if body['action']:
                return HttpResponse.InternalServerError('Internal error!', str(e), body['action'])
            return HttpResponse.InternalServerError('Internal error!', str(e))


# Função para configurar e iniciar a aplicação
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
