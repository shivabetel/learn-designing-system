class OutOfStockException(Exception):
    message = "Out of stock"
    def __init__(self, message: str = message):
        self.message = message
    def __str__(self):
        return self.message