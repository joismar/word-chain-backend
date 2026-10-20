import json
import os
import time
from typing import Callable, Optional

from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from api_gateway_service import ConnectionGateway
from game import Game
from messages.messages_pt import ErrorMessage
from protocol import models as wire
from utils import wordlist
from utils.errors import ConcurrentUpdateError, GameException

SERVICE = 'word-chain'
MAX_ATTEMPTS = 3
OK = {'statusCode': 200}

logger = Logger(service=SERVICE)
tracer = Tracer(service=SERVICE)


def now_ms() -> int:
    return int(time.time() * 1000)


class GameApplication:
    """Routes API Gateway WebSocket events to Game.

    Replies go out through the management API (not the Lambda return
    value), so every route behaves the same whether or not it has a route
    response configured.
    """

    def __init__(self, session_repository, player_repository, gateway,
                 clock: Callable[[], int] = now_ms,
                 words_loader: Callable = wordlist.load):
        self.session_repository = session_repository
        self.player_repository = player_repository
        self.gateway = gateway
        self.clock = clock
        self.words_loader = words_loader

    def run(self, event) -> dict:
        context = event['requestContext']
        connection_id = context['connectionId']
        route = context['routeKey']
        logger.append_keys(connection_id=connection_id, route=route)

        if route == '$connect':
            return OK

        if route == '$disconnect':
            try:
                self.__with_retries(connection_id, lambda game: game.disconnect())
            except Exception:
                logger.exception('disconnect failed')
            return OK

        reply = self.__handle_message(connection_id, event.get('body'))
        self.gateway.send(connection_id, wire.to_wire(reply))
        return OK

    def __handle_message(self, connection_id: str, body: Optional[str]):
        try:
            raw = json.loads(body or '')
        except ValueError:
            return self.__error(None, ErrorMessage.INVALID_MESSAGE)

        if not isinstance(raw, dict):
            return self.__error(None, ErrorMessage.INVALID_MESSAGE)
        request_id = raw.get('requestId')
        if not isinstance(request_id, str) or not 0 < len(request_id) <= wire.MAX_REQUEST_ID_LENGTH:
            request_id = None
        if raw.get('v') != wire.PROTOCOL_VERSION:
            return self.__error(request_id, ErrorMessage.UNSUPPORTED_VERSION)

        try:
            message = wire.client_message_adapter.validate_python(raw)
        except ValidationError as error:
            logger.info('invalid message', extra={
                'errors': error.errors(include_url=False, include_input=False)})
            return self.__error(request_id, ErrorMessage.INVALID_MESSAGE)

        logger.append_keys(request_id=message.request_id, message_type=message.type)
        try:
            return self.__with_retries(connection_id, lambda game: game.handle(message))
        except GameException as error:
            logger.info('game error', extra={'code': error.code})
            return self.__error(request_id, ErrorMessage[error.code])
        except ConcurrentUpdateError:
            logger.warning('gave up after concurrent updates')
            return self.__error(request_id, ErrorMessage.CONCURRENT_UPDATE)
        except Exception:
            logger.exception('unhandled error')
            return self.__error(request_id, ErrorMessage.INTERNAL_ERROR)

    def __with_retries(self, connection_id: str, action):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            game = Game(self.session_repository, self.player_repository, self.gateway,
                        connection_id=connection_id, now=self.clock(),
                        words_loader=self.words_loader)
            try:
                return action(game)
            except ConcurrentUpdateError:
                if attempt == MAX_ATTEMPTS:
                    raise
                logger.info('concurrent update, retrying', extra={'attempt': attempt})

    @staticmethod
    def __error(request_id: Optional[str], error: ErrorMessage):
        return wire.ErrorReply(request_id=request_id,
                               payload=wire.ErrorPayload(code=error.name, message=error.value))


_application: Optional[GameApplication] = None


def _get_application() -> GameApplication:
    # Built once per container so boto3 clients and tables are reused.
    global _application
    if _application is None:
        from repository.player_repository import PlayerRepository
        from repository.session_repository import SessionRepository

        player_repository = PlayerRepository()
        _application = GameApplication(
            SessionRepository(player_repository),
            player_repository,
            ConnectionGateway.from_endpoint(os.environ.get('API_GATEWAY_URL')),
        )
    return _application


@logger.inject_lambda_context(correlation_id_path='requestContext.requestId', clear_state=True)
@tracer.capture_lambda_handler
def main(event, context):
    return _get_application().run(event)
