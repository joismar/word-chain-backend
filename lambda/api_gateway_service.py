from concurrent.futures import ThreadPoolExecutor
import json

import boto3
from aws_lambda_powertools import Logger

MAX_PARALLEL_SENDS = 10

logger = Logger(child=True)


class ConnectionGateway:
    """Pushes messages to WebSocket connections through the management API."""

    def __init__(self, client):
        self.client = client

    @classmethod
    def from_endpoint(cls, endpoint_url: str):
        return cls(boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url))

    def send(self, connection_id: str, message: dict) -> bool:
        """Returns False when the connection is gone."""
        return self.__post(connection_id, json.dumps(message).encode('utf-8'))

    def broadcast(self, connection_ids: list[str], message: dict) -> list[str]:
        """Sends in parallel; returns the ids of connections that are gone."""
        if not connection_ids:
            return []
        data = json.dumps(message).encode('utf-8')
        workers = min(MAX_PARALLEL_SENDS, len(connection_ids))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            delivered = list(pool.map(lambda cid: self.__post(cid, data), connection_ids))
        return [cid for cid, ok in zip(connection_ids, delivered) if not ok]

    def __post(self, connection_id: str, data: bytes) -> bool:
        try:
            self.client.post_to_connection(Data=data, ConnectionId=connection_id)
            return True
        except self.client.exceptions.GoneException:
            return False
        except Exception:
            # A transient failure is not proof the client left; keep it.
            logger.exception('post_to_connection failed', extra={'connection_id': connection_id})
            return True
