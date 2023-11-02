import os

from dotenv import load_dotenv

from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection

from models.bitcoin_data import (
    BITCOIN_TO_SATOSHI,
    DUPLICATE_TRANSACTIONS,
    Block,
    Tx,
    Output,
    Input,
    Address
)
from blockchain_data_provider import PersistentBlockchainAPIData

load_dotenv()

JANUSGRAPH_HOST = os.getenv("JANUSGRAPH_HOST")
JANUSGRAPH_PORT = os.getenv("JANUSGRAPH_PORT")
JANUSGRAPH_URL = f"ws://{JANUSGRAPH_HOST}:{JANUSGRAPH_PORT}/gremlin"


g = traversal().with_remote(DriverRemoteConnection(JANUSGRAPH_URL, 'g'))


def chunked_ranges(lowest, highest, buffer: int = 100) -> list[tuple[int, int]]:

    ranges = []

    total = highest - lowest + 1
    if buffer > total:
        buffer = total

    start = lowest
    if buffer > 0:
        while start <= highest - buffer + 1:
            ranges.append((start, start + buffer - 1))
            start += buffer

        remaining_blocks = highest - start + 1
        if remaining_blocks > 0:
            ranges.append((highest - remaining_blocks + 1 * (start > lowest), highest))
    else:
        ranges.append((0, 0))

    return ranges


def chunked_indices(items: list, buffer: int):
    return [(start, end + 1) for (start, end) in chunked_ranges(0, len(items) - 1, buffer)]


def haircut(ctn_input_value: float, sum_of_inputs: int, output_value: float) -> float:
    """
    Generic haircut function that finds the contribution of a single input to an output.
    """
    return (ctn_input_value / sum_of_inputs) * output_value


class OutputGraphPopulate:
    pass