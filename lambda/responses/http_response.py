import json
from utils.errors import GameException


class HttpResponse:
    @classmethod
    def InternalServerError(cls, error: Exception | GameException, action: str = None):
        message = getattr(error, 'message', str(error))
        code = getattr(error, 'code', type(error).__name__)
        body = {'message': message, 'error': code}
        return {
            'statusCode': 500,
            'body': json.dumps({'action': action, 'data': body})
        }

    @classmethod
    def BadRequest(cls, error: Exception | GameException, action: str = None):
        message = getattr(error, 'message', str(error))
        code = getattr(error, 'code', type(error).__name__)
        body = {'message': message, 'error': code}
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
