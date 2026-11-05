from enum import Enum


class ErrorMessage(str, Enum):
    """The member names are the protocol's error codes; never rename one."""
    INEXISTENT_SESSION = "Sessão não existe."
    INEXISTENT_PLAYER = "Jogador não existe."
    ALL_PLAYERS_NEED_READY = "Todos os jogadores precisam estar prontos."
    INVALID_TURN = "Turno de jogador inválido."
    INEXISTENT_WORD = "Palavra não existe."
    WORD_ALREADY_IN_GAME = "Palavra já foi usada no jogo."
    NO_POINTS = "A palavra não formou pontos."
    GAME_STARTED = "Não é permitido entrar em um jogo em execução."
    NOT_HOST = "Apenas o jogador que criou a sala pode fazer isso."
    ROOM_FULL = "A sala está cheia."
    GAME_NOT_STARTED = "A partida ainda não começou."
    GAME_FINISHED = "A partida já terminou."
    DEADLINE_NOT_REACHED = "O tempo ainda não acabou."
    INVALID_MESSAGE = "Mensagem inválida."
    UNSUPPORTED_VERSION = "Versão do protocolo não suportada. Atualize a página."
    CONCURRENT_UPDATE = "Outra jogada aconteceu ao mesmo tempo. Tente de novo."
    INTERNAL_ERROR = "Erro interno do servidor."
