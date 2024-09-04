import json


class HttpResponse:
    @classmethod
    def InternalServerError(cls, message: str, error='Internal error', action: str = None):
        body = {'message': message, 'error': error}
        return {
            'statusCode': 500,
            'body': json.dumps({'action': action, 'data': body})
        }

    @classmethod
    def BadRequest(cls, message: str, error='Application error', action: str = None):
        body = {'message': message, 'error': error}
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
