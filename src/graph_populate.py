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

from graph.base import g


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


def haircut(input_value: float, sum_of_inputs: int, output_value: float) -> float:
    """
    Generic haircut function that finds the contribution of a single input to an output.
    """
    return (input_value / sum_of_inputs) * output_value


class OutputGraphPopulate:
    pass
