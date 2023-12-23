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
from blockchain_data_provider import BlockchainDataProviderADT, chunked_indices, chunked_ranges

from graph.base import g


def haircut(input_value: float, sum_of_inputs: int, output_value: float) -> float:
    """
    Generic haircut function that finds the contribution of a single input to an output.
    """
    return (input_value / sum_of_inputs) * output_value


class PopulateOutputProportionGraph:

    def __init__(self,
                 data_provider: BlockchainDataProviderADT = None):
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
        
        highest_to_populate = block_heights[-1]

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

        height = 0

        tx: Tx
        for tx in self.data_provider.get_txs_for_blocks(session, min_height=0, max_height=highest_to_populate, buffer=1000):

            tx_sum = tx.total_input_value()
            output: Output
            for output in tx.outputs:
                if not output.valid:
                    continue

                # create a new output node if it doesn't exist
                output_node = g.V().has('output', 'id', output.id).fold().coalesce(
                    __.unfold(),
                    __.addV('output').property('id', output.id)
                ).next()

                # create a new address node if it doesn't exist
                address_node = g.V().has('address', 'id', output.address.id).fold().coalesce(
                    __.unfold(),
                    __.addV('address').property('id', output.address.id)
                ).next()

                # connect the address node to the output node
                g.V(output_node).addE('has_address').to(address_node).next()

                input: Input
                for input in tx.inputs:
                    haircut_value = haircut(input.prev_out.value, tx_sum, output.value)
                    g.addE('sent') \
                        .from_(__.V().has('id', input.prev_out.id)) \
                        .to(output_node) \
                        .property('value', haircut_value).next()
                        
                if tx.block_height > height:
                    height = tx.block_height
                    if show_progressbar:
                        block_heights.update(1)


if __name__ == '__main__':
    import argparse

    from models.base import SessionLocal
    from blockchain_data_provider import PersistentBlockchainAPIData

    parser = argparse.ArgumentParser(description="Script for populating database")
    parser.add_argument('--height', default=None, type=int, help='Block height up to which to populate')
    parser.add_argument('--delete', default=False, action='store_true',
                        help='Delete all data in database and don\'t populate.')

    args = parser.parse_args()

    data_provider = PersistentBlockchainAPIData()

    populator = PopulateOutputProportionGraph(data_provider)

    with SessionLocal() as session:

        if args.delete:
            print("Deleting all graph data...")
            # wipe the database
            populator.clear_graph()
            print("Graph data wiped.")
            exit(0)
        else:
            print("Populating graph...")

            if args.height is not None:
                # highest_block: Block = session.query(Block).get(args.height)
                highest_block: Block = session.get(Block, args.height)
            else:
                highest_block: Block = session.query(Block).order_by(Block.height.desc()).first()

            if not highest_block:
                print("No blocks found in database. Cannot populate graph. Exiting.")
                exit(1)
            else:
                populator.clear_graph()
                populator.populate(session,
                                   range(0, highest_block.height + 1),
                                   show_progressbar=True)
