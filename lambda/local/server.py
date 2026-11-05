"""Local WebSocket server that stands in for API Gateway + DynamoDB.

Runs the real GameApplication with in-memory repositories, so the client
can be tested end to end without deploying:

    cd lambda
    python -m local.server --port 3001

Then point the client at it (VITE_WS_URL=ws://localhost:3001). State lives
in memory and is lost on restart. Messages are handled one at a time, so the
concurrency paths (ConcurrentUpdateError retries) are not exercised here.
"""
import argparse
import asyncio
import json
import os
import threading
import uuid

os.environ.setdefault('POWERTOOLS_TRACE_DISABLED', '1')
os.environ.setdefault('POWERTOOLS_LOG_LEVEL', 'WARNING')

from websockets.asyncio.server import ServerConnection, serve  # noqa: E402
from websockets.exceptions import ConnectionClosed  # noqa: E402

from local.memory import MemoryPlayerRepository, MemorySessionRepository  # noqa: E402
from main import GameApplication  # noqa: E402

SEND_TIMEOUT_S = 5


class LocalGateway:
    """ConnectionGateway over live websockets, callable from worker threads."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.connections: dict[str, ServerConnection] = {}

    def send(self, connection_id: str, message: dict) -> bool:
        websocket = self.connections.get(connection_id)
        if websocket is None:
            return False
        future = asyncio.run_coroutine_threadsafe(websocket.send(json.dumps(message)), self.loop)
        try:
            future.result(SEND_TIMEOUT_S)
            return True
        except ConnectionClosed:
            return False

    def broadcast(self, connection_ids: list[str], message: dict) -> list[str]:
        return [cid for cid in connection_ids if not self.send(cid, message)]


def event(connection_id: str, route: str, body: str | None = None) -> dict:
    context = {'connectionId': connection_id, 'routeKey': route,
               'requestId': uuid.uuid4().hex}
    return {'requestContext': context, **({'body': body} if body is not None else {})}


async def main(host: str, port: int) -> None:
    loop = asyncio.get_running_loop()
    gateway = LocalGateway(loop)
    players = MemoryPlayerRepository()
    app = GameApplication(MemorySessionRepository(players), players, gateway)
    # One message at a time, like a single Lambda container.
    lock = threading.Lock()

    def run(e: dict) -> None:
        with lock:
            app.run(e)

    async def handle(websocket: ServerConnection) -> None:
        # API Gateway ids are opaque base64-ish strings; any unique string works.
        connection_id = uuid.uuid4().hex[:16]
        gateway.connections[connection_id] = websocket
        print(f'+ {connection_id}')
        await asyncio.to_thread(run, event(connection_id, '$connect'))
        try:
            async for body in websocket:
                await asyncio.to_thread(run, event(connection_id, '$default', str(body)))
        except ConnectionClosed:
            pass
        finally:
            gateway.connections.pop(connection_id, None)
            await asyncio.to_thread(run, event(connection_id, '$disconnect'))
            print(f'- {connection_id}')

    async with serve(handle, host, port):
        print(f'Word Chain local server on ws://{host}:{port}')
        await asyncio.get_running_loop().create_future()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3001)
    args = parser.parse_args()
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        pass
