from transmit.data import Data

class Node_to_Tracker(Data):
    def __init__(self, node_id: int, mode: int, metadata: dict, Id, downloaded_sum: int = 0, magnet_link: str = ""):
        
        super().__init__()
        self.node_id = node_id
        self.mode = mode
        self.Id = Id
        self.metadata = metadata
        self.downloaded_sum = downloaded_sum
        self.magnet_link = magnet_link





