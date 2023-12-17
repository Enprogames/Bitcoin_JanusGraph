from sqlalchemy.orm import Session
from gremlin_python.process.traversal import T
from gremlin_python.process.graph_traversal import __

from models.bitcoin_data import (
    BITCOIN_TO_SATOSHI,
    DUPLICATE_TRANSACTIONS,
    Block,
    Tx,
    Output,
    Input,
    Address
)
from blockchain_data_provider import (
    BlockchainAPIJSON,
    PersistentBlockchainAPIData
)

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
            ranges.append((highest - remaining_blocks +
                          1 * (start > lowest), highest))
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


class PopulateOutputProportionGraph:

    def __init__(self,
                 data_provider: BlockchainAPIJSON = None):
        self.data_provider = data_provider

    def clear_graph(self):
        g.V().drop().iterate()

    def populate(self,
                 session: Session,
                 block_heights: list[int],
                 show_progressbar=False,
                 fail_if_exists=False):

        block_heights = list(block_heights)
        block_heights.sort()

        highest_id = g.V().hasLabel('output').values('id').max().toList()

        assert len(highest_id) < 2, "more than one highest id returned"

        if highest_id:
            highest_id = highest_id[0]
            highest_block = session.query(Block.height)\
                .join(Tx, Block.transactions)\
                .join(Output, Tx.outputs)\
                .filter(Output.id == highest_id)\
                .order_by(Block.height.desc())\
                .first().height

            if highest_block in block_heights and fail_if_exists:
                raise ValueError(f"highest block {highest_block} is in block heights")

        if show_progressbar:
            from tqdm import tqdm
            block_heights = tqdm(block_heights)

        for height in block_heights:
            block = self.data_provider.get_block(session, height)

            for tx in block.transactions:

                tx_sum = tx.total_input_value()
                for output in tx.outputs:
                    if not output.valid:
                        continue

                    output_node = g.addV('output').property(
                        "id", output.id).next()
                    for input in tx.inputs:
                        haircut_value = haircut(input.prev_out.value, tx_sum, output.value)
                        g.addE('sent') \
                            .from_(__.V().has('id', input.prev_out.id)) \
                            .to(output_node) \
                            .property('value', haircut_value).next()


if __name__ == '__main__':
    from models.base import SessionLocal

    from blockchain_data_provider import PersistentBlockchainAPIData

    data_provider = PersistentBlockchainAPIData()

    populator = PopulateOutputProportionGraph(data_provider)

    with SessionLocal() as session:
        highest_block = session.query(Block).order_by(Block.height.desc()).first()

        if not highest_block:
            print("No blocks found in database. Cannot populate graph. Exiting.")
            exit(1)
        else:
            populator.clear_graph()
            populator.populate(session,
                               range(0, highest_block.height+1),
                               show_progressbar=True)
