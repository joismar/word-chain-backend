from messages.messages_pt import ErrorMessage


class GameException(Exception):
    def __init__(self, error: ErrorMessage):
        super().__init__(error.value)
        self.message = error.value
        self.code = error.name


class ConcurrentUpdateError(Exception):
    """The session changed between our read and our conditional write."""
