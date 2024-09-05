from messages.messages_pt import ErrorMessage


class GameException(Exception):
    def __init__(self, error: ErrorMessage, action: str = None):
        self.message = error.value
        self.code = error.name
        self.action = action