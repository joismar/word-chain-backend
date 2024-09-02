class RepositoryManager:
    _instance = None
    _repository = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_repository(cls, repository):
        cls._repository = repository

    @classmethod
    def save(cls, entity):
        if cls._repository is not None:
            cls._repository.save(entity)
        else:
            raise ValueError("Repository not set.")