import json
from utils.errors import GameException


class HttpResponse:
    @classmethod
    def InternalServerError(cls, error: Exception | GameException, action: str = None):
        body = {'message': error.message, 'error': error.code}
        return {
            'statusCode': 500,
            'body': json.dumps({'action': action, 'data': body})
        }

    @classmethod
    def BadRequest(cls, error: Exception | GameException, action: str = None):
        body = {'message': error.message, 'error': error.code}
        return {
            'statusCode': 400,
            'body': json.dumps({'action': action, 'data': body})
        }

    @classmethod
    def Ok(cls, action: str = None, body: dict = None):
        return {
            'statusCode': 200,
            'body': json.dumps({'action': action, **body}) if (action and body) else ''
        }
