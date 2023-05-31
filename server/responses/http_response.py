import json


class HttpResponse:
    @classmethod
    def InternalServerError(cls, message: str, error=None):
        return {
            'statusCode': 500,
            'body': json.dumps({'message': message, 'error': error})
        }

    @classmethod
    def BadRequest(cls, message: str, error=None):
        return {
            'statusCode': 400,
            'body': json.dumps({'message': message, 'error': error})
        }

    @classmethod
    def Ok(cls, action: str = None, body: dict = None):
        return {
            'statusCode': 200,
            'body': json.dumps({'action': action, **body}) if (action and body) else ''
        }
