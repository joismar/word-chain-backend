import json


class HttpResponse():
  @classmethod
  def InternalServerError(cls, message: str, error = None):
    return {
      'statusCode': 500,
      'body': json.dumps({'message': message, 'error': error})
    }
  
  @classmethod
  def BadRequest(cls, message: str):
    return {
      'statusCode': 400,
      'body': json.dumps({'message': message})
    }
  
  @classmethod
  def Ok(cls, body: dict):
    return {
      'statusCode': 200,
      'body': json.dumps(body)
    }
