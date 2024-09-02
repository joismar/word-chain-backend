import boto3


class ApiGatewayService:
    def __init__(self, endpoint_url: str):
        self.client = boto3.client(
            'apigatewaymanagementapi', endpoint_url=endpoint_url)
