class UserAlreadyPurchasedException(Exception):
    message = "User already purchased"
    def __init__(self, message: str = message):
        self.message = message

    def __str__(self):
        return self.message