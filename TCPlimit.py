from config import config

class TCPlimit:
    def __init__(self, data: bytes):

        assert len(data) <= config.const["TCP_LIMIT"], print(
            f"MAXIMUM DATA SIZE OF A TCP SEGMENT IS {config.const['TCP_LIMIT']}, While the data size is {len(data)}"
        )

        self.length = len(data)
        self.data = data


