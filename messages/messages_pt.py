from enum import Enum


class Message(str, Enum):
    CHAINED = "Você formou uma CORRENTE com {} pontos!"
    POINTS = "Você ganhou {} pontos!"


class Error(str, Enum):
    INEXISTENT_SESSION = "Sessão não existe."
    INEXISTENT_PLAYER = "Jogador não existe."
    ALL_PLAYERS_NEED_READY = "Todos os jogadores precisam estar prontos."
    INVALID_TURN = "Turno de jogador inválido."
    INEXISTENT_WORD = "Palavra não existe."
    WORD_ALREADY_IN_GAME = "Palavra já foi usada no jogo."
    NO_POINTS = "A palavra não formou pontos."
    GAME_STARTED = "Não é permitido entrar em um jogo em execução."
