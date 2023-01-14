import math
from typing import List, Any


class Partition:
    items: List[Any]
    partition_size: int

    def __init__(self, items: List[Any], partition_size: int = 50):
        self.items = items
        self.partition_size = partition_size

    def __getitem__(self, subscript):
        if isinstance(subscript, int):
            if subscript < 0:  # Handle negative indices
                raise IndexError("The index (%d) is negative." % subscript)
            if subscript < 0 or subscript >= len(self):
                raise IndexError("The index (%d) is out of range." % subscript)
            return self.items[subscript * self.partition_size:subscript * self.partition_size + self.partition_size]

    def __len__(self):
        return math.ceil(len(self.items) / self.partition_size)

