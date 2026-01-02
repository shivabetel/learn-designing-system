class VoteAlreadyExistsException(Exception):
    message = "Vote already exists"

    def __init__(self, message: str = message):
        self.message = message

    def __str__(self):
        return self.message
