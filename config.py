class Config:
    """Config class which contains directories, constants, etc."""

    def __init__(self):
        self.dir = {
            # "logs_dir": "logs/",
            "node_dir": "node/",
            # "tracker_db_dir": "tracker_db/"
        }
        self.const = {
            "AVAILABLE_PORTS_RANGE": (1024, 65535),
            "TRACKER_ADDR": ("192.168.1.8", 22236),
            "TCP_LIMIT": 65535,
            "BUFFER_SIZE": 9216,
            "CHUNK_PIECES_SIZE": 50000,
            "MAX_SPLITTNES_RATE": 3,
            "NODE_TIME_INTERVAL": 30,
            "TRACKER_TIME_INTERVAL": 30
        }
        self.tracker_requests = {
            "REQUEST": 0,
            "UPLOAD": 1,
            "DOWNLOAD": 2,
            # "UPDATE": 3,
            "EXIT": 4
        }


# Example of usage
config = Config()



