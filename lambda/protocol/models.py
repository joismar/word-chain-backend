"""Word Chain wire protocol, version 2.

These models are the single source of truth for the protocol. The JSON Schema
in protocol/v2.schema.json is exported from them (python -m protocol.export_schema)
and the client's zod schema is built from that file.

Every message is an envelope: {"v": 2, "type": ..., "payload": ..., "requestId": ...}.
Field names on the wire are camelCase.
"""
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.alias_generators import to_camel

from messages.messages_pt import ErrorMessage

PROTOCOL_VERSION = 2

MIN_GAME_MINUTES = 1
MAX_GAME_MINUTES = 30
MAX_NAME_LENGTH = 20
MAX_WORD_LENGTH = 40
MAX_REQUEST_ID_LENGTH = 64


class WireModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra='forbid',
        frozen=True,
        str_strip_whitespace=True,
        # Exported in serialization mode: what the server sends always has
        # every field, so defaults must still be required in the schema.
        json_schema_serialization_defaults_required=True,
    )


PlayerStatus = Literal['waiting', 'ready', 'playing', 'offline']
GameStatus = Literal['lobby', 'playing', 'finished']
PlayerColor = Literal['red', 'blue', 'green', 'yellow',
                      'purple', 'orange', 'pink', 'brown']
ErrorCode = Literal[tuple(error.name for error in ErrorMessage)]

Name = Annotated[str, Field(min_length=1, max_length=MAX_NAME_LENGTH)]
RequestId = Annotated[str, Field(min_length=1, max_length=MAX_REQUEST_ID_LENGTH)]
EpochMs = Annotated[int, Field(ge=0, description='Unix time in milliseconds')]


# ---------------------------------------------------------------- shared

class GameConfig(WireModel):
    time: int = Field(ge=MIN_GAME_MINUTES, le=MAX_GAME_MINUTES,
                      description='Match length in minutes')
    repetition: bool = Field(description='Whether a word may be played again')


class Player(WireModel):
    id: str
    name: str
    score: int
    status: PlayerStatus
    color: Optional[PlayerColor]


class ChainWord(WireModel):
    word: str
    player_id: Optional[str] = Field(
        description='Null for the word the server seeds the chain with')


class GameState(WireModel):
    name: str = Field(description='Room code players type to join')
    status: GameStatus
    players: list[Player] = Field(description='In turn order; the first one is the host')
    chain: list[ChainWord]
    host_id: Optional[str]
    turn_player_id: Optional[str]
    config: GameConfig
    started_at: Optional[EpochMs] = Field(
        description='When play begins (after the start countdown)')
    ends_at: Optional[EpochMs]
    turn_deadline: Optional[EpochMs] = Field(
        description='Null when there is no turn timer (single active player)')
    server_time: EpochMs = Field(
        description='Server clock when this state was sent, to offset local timers')
    version: int = Field(ge=0)


# ------------------------------------------------------- client -> server

class HostPayload(WireModel):
    player_name: Name


class JoinPayload(WireModel):
    room_name: Name
    player_name: Name


class ReadyPayload(WireModel):
    ready: bool


class StartPayload(WireModel):
    config: GameConfig


class WordPayload(WireModel):
    word: Annotated[str, Field(min_length=1, max_length=MAX_WORD_LENGTH)]


class ReconnectPayload(WireModel):
    player_id: Annotated[str, Field(min_length=1)]


class EmptyPayload(WireModel):
    pass


class ClientEnvelope(WireModel):
    v: Literal[2]
    request_id: RequestId


class HostMessage(ClientEnvelope):
    type: Literal['host']
    payload: HostPayload


class JoinMessage(ClientEnvelope):
    type: Literal['join']
    payload: JoinPayload


class ReadyMessage(ClientEnvelope):
    type: Literal['ready']
    payload: ReadyPayload


class StartMessage(ClientEnvelope):
    type: Literal['start']
    payload: StartPayload


class WordMessage(ClientEnvelope):
    type: Literal['word']
    payload: WordPayload


class PassMessage(ClientEnvelope):
    type: Literal['pass']
    payload: EmptyPayload


class TimeoutMessage(ClientEnvelope):
    """Sent when a deadline expires locally. Accepted only if it expired on the server too."""
    type: Literal['timeout']
    payload: EmptyPayload


class ReconnectMessage(ClientEnvelope):
    type: Literal['reconnect']
    payload: ReconnectPayload


ClientMessage = Annotated[
    Union[HostMessage, JoinMessage, ReadyMessage, StartMessage, WordMessage,
          PassMessage, TimeoutMessage, ReconnectMessage],
    Field(discriminator='type'),
]
client_message_adapter = TypeAdapter(ClientMessage)


# ------------------------------------------------------- server -> client

class SessionPayload(WireModel):
    player: Player = Field(description='The player this connection controls')
    game: GameState


class AckPayload(WireModel):
    points: Optional[int] = Field(default=None, description='Only on word')
    chain_points: Optional[int] = Field(default=None, description='Only on word')


class ErrorPayload(WireModel):
    code: ErrorCode
    message: str = Field(description='Human-readable, pt-BR')


class ServerEnvelope(WireModel):
    v: Literal[2] = PROTOCOL_VERSION


class SessionMessage(ServerEnvelope):
    """Reply to host, join and reconnect."""
    type: Literal['session'] = 'session'
    request_id: RequestId
    payload: SessionPayload


class AckMessage(ServerEnvelope):
    """Reply to ready, start, word, pass and timeout."""
    type: Literal['ack'] = 'ack'
    request_id: RequestId
    payload: AckPayload


class ErrorReply(ServerEnvelope):
    type: Literal['error'] = 'error'
    request_id: Optional[RequestId] = Field(
        description='Null when the request could not be parsed')
    payload: ErrorPayload


class GameStateMessage(ServerEnvelope):
    """Broadcast to every player in the room whenever the game changes."""
    type: Literal['game_state'] = 'game_state'
    payload: GameState


ServerMessage = Annotated[
    Union[SessionMessage, AckMessage, ErrorReply, GameStateMessage],
    Field(discriminator='type'),
]
server_message_adapter = TypeAdapter(ServerMessage)


class Protocol(WireModel):
    """Wrapper used only to export both directions into one JSON Schema."""
    client: ClientMessage
    server: ServerMessage


def to_wire(message: BaseModel) -> dict:
    return message.model_dump(by_alias=True, mode='json')
