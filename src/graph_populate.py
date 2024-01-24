import time
from sqlalchemy.orm import Session, joinedload
from gremlin_python.process.traversal import T
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.protocol import GremlinServerError

from models.bitcoin_data import (
    BITCOIN_TO_SATOSHI,
    DUPLICATE_TRANSACTIONS,
    Block,
    Tx,
    Output,
    Input,
    Address
)

from models.bitcoin_data import ManualProportion

from blockchain_data_provider import BlockchainDataProviderADT, chunked_indices, chunked_ranges

from graph.base import g


def haircut(input_value: float, sum_of_inputs: int, output_value: float) -> float:
    """
    Generic haircut function that finds the contribution of a single input to an output.
    haircut_value = (input_value / sum_of_inputs) * output_value
    """
    return (input_value / sum_of_inputs) * output_value


def calculate_proportions(input_values, output_values, manual_proportions):
    """
    We are using the haircut method to proportionally distribute input values
    to output values. But sometimes it is also important that manual proportions
    can be set.

    This function takes in a transaction and a list of manual input-to-output
    proportions and returns a list of input-to-output values.

    The output format will be an adjacency matrix specifying the values
    for each input-to-output pair. The input and output indices are the
    indices of the input_values and output_values lists.

    For example, if we have an input at index 0 with value 5, and an output
    at index 2 with value 6, and we send 0.5 of the input to the output, then
    the output of this function will include 2.5 at index (0, 2).

    This process is tricky since we have to force certain input-to-output
    pairs to have certain proportions, while also maintaining the haircut
    distributions. For instances, if we send 0.5 of an input to an output,
    the haircut method will try to force more from that input to the output.
    So we need to re-distribute the remainder of this input-to-output
    amount to the other outputs.

    It is easy to check the correctness of the final values. The sum of the
    final values for each input-to-output pair should equal the sum
    of the output values. And the values for the manual proportions should
    be as specified.
    """
    result = [[0 for _ in output_values] for _ in input_values]
    remaining_input_values = input_values.copy()
    remaining_output_values = output_values.copy()

    # First, we distribute the manual proportions
    # If any proportion is greater than 1, or causes the input value to
    # be greater than the output value, then we raise an error
    for manual_proportion in manual_proportions:
        o = manual_proportion.output.index_in_tx
        i = manual_proportion.input.index_in_tx
        p = manual_proportion.proportion
        result[i][o] = input_values[i] * p
        remaining_input_values[i] -= result[i][o]
        remaining_output_values[o] -= result[i][o]
        if p > 1:
            raise ValueError("Manual proportion cannot be greater than 1")
        if result[i][o] > input_values[i]:
            raise ValueError("Manual proportion cannot be greater than input value")
        if result[i][o] > output_values[o]:
            raise ValueError("Manual proportion cannot be greater than output value")

    # collect together all non-manual edges, and sum their values
    non_manual_edges = []
    non_manual_sum = 0

    remaining_values_sum = sum(remaining_input_values)
    if remaining_values_sum > 0:
        # Next, distribute the remaining values proportionally. But when we
        # reach an input-to-output pair that has a manual proportion, we
        # need to distribute the remaining values to the other outputs.
        # This is done by first skipping these edges, then calculating the
        # remaining values and distributing them later.
        amount_remaining = 0
        for o, output_value in enumerate(remaining_output_values):
            for i, input_value in enumerate(remaining_input_values):
                if result[i][o] > 0:
                    amount_remaining += output_value * input_value / remaining_values_sum
                    continue
                result[i][o] += output_value * input_value / remaining_values_sum
                non_manual_edges.append((i, o, result[i][o]))
                non_manual_sum += result[i][o]

        # Finally, distribute the remaining values to the other outputs
        # Value is attributed based on what proportion each non-manual edge
        # has of the total non-manual sum
        for i, o, _ in non_manual_edges:
            result[i][o] += amount_remaining * (result[i][o] / non_manual_sum)

    return result


class PopulateOutputProportionGraph:

    def __init__(self,
                 data_provider: BlockchainDataProviderADT = None):
        self.data_provider = data_provider

    def clear_graph(self, batch_size: int = 100_000):
        # Not all vertices can be deleted at once, so we delete them in batches.
        try:
            while g.V().limit(1).count().next() > 0:
                g.V().limit(batch_size).drop().iterate()
        except GremlinServerError:
            print("Gremlin server error. Consider descreasing batch size or increasing evaluationTimeout")

    def get_highest_block_height(self, session: Session):
        highest_block = session.query(Block.height).order_by(Block.height.desc()).first()

        if highest_block:
            return highest_block.height
        else:
            return -1

    def get_highest_vertex_id(self) -> int:
        start = time.perf_counter()
        highest_id = g.V().values('id').max().toList()
        print(f"Got highest ID vertex in {time.perf_counter() - start} seconds")

        assert len(highest_id) < 2, "more than one highest id returned"

        if highest_id:
            return highest_id[0]
        else:
            return -1

    def upsert_haircut_edge(self, prev_out_id: int, output_id: int, haircut_value: float):
        g.V().has('output_id', prev_out_id) \
             .inE('sent').where(__.outV().has('output_id', output_id)) \
             .fold() \
             .coalesce(__.unfold(),
                       __.V().has('output', 'output_id', output_id)
                       .addE('sent')
                       .from_(__.V().has('output', 'output_id', prev_out_id))
                       .property('value', haircut_value)
                       ).next()

    def apply_manual_edge_proportions_for_tx(
        self,
        session: Session,
        tx_id: int
    ):
        tx = session.query(Tx)\
                    .options(
                        joinedload(Tx.inputs)
                        .joinedload(Input.prev_out),
                        joinedload(Tx.outputs)
                     )\
                    .filter_by(id=tx_id)\
                    .first()

        # Delete existing edges from this input to outputs within the same transaction
        for output in tx.outputs:
            g.V().has('output_id', output.id)\
                .inE('sent').drop().iterate()

        # retrieve all manual proportions whose output is in this transaction
        manual_proportions = session.query(ManualProportion)\
                                    .join(Output, ManualProportion.output)\
                                    .filter(Output.tx_id == tx.id)\
                                    .options(
                                        joinedload(ManualProportion.input).joinedload(Input.prev_out),
                                        joinedload(ManualProportion.output)
        ).all()

        # create list of remaining values for each input/output
        input_values = [input.prev_out.value for input in tx.inputs]
        output_values = [output.value for output in tx.outputs]

        edge_values = calculate_proportions(input_values, output_values, manual_proportions)

        output: Output
        for output in tx.outputs:
            # If the output value is 0, no edges should be created
            if output_values[output.index_in_tx] == 0:
                continue

            # Recalculate and upsert other edges based on the remaining transaction value
            input: Input
            for input in tx.inputs:
                # If the input value is 0, no edges should be created
                if input_values[input.index_in_tx] == 0:
                    continue

                edge_value = edge_values[input.index_in_tx][output.index_in_tx]
                if edge_value > 0:
                    self.upsert_haircut_edge(input.prev_out.id, output.id, edge_value)

    def apply_manual_edge_proportions(
        self,
        session: Session,
        show_progressbar=False
    ):
        if show_progressbar:
            from tqdm import tqdm
            manual_proportions_count = session.query(ManualProportion).count()
            progressbar = tqdm(total=manual_proportions_count, desc="Applying manual edge proportions", unit="edge")

        affected_tx_ids = session.query(Tx.id)\
                                 .join(Output, Tx.id == Output.tx_id)\
                                 .join(ManualProportion, Output.id == ManualProportion.output_id)\
                                 .distinct().all()

        for tx in affected_tx_ids:
            self.apply_manual_edge_proportions_for_tx(session, tx.id)

            if show_progressbar:
                progressbar.update(1)

        if show_progressbar:
            progressbar.close()

    def reset_manual_edge_proportions(
        self,
        session: Session,
        show_progressbar=False
    ):
        affected_txs = ManualProportion.get_affected_txs(session)

        if show_progressbar:
            from tqdm import tqdm
            tx_count = len(affected_txs)
            progressbar = tqdm(total=tx_count, desc="Resetting edge proportions", unit="edge")

        for tx in affected_txs:
            tx_sum = tx.total_input_value()
            # Delete existing edges from this input to outputs within the same transaction
            for output in tx.outputs:
                g.V().has('output_id', output.id)\
                    .inE('sent').drop().iterate()
            if tx_sum == 0:
                progressbar.update(1)
                continue

            # Recalculate and upsert edges for outputs in this transaction
            output: Output
            for output in tx.outputs:
                input: Input
                for input in tx.inputs:
                    haircut_value = haircut(input.prev_out.value, tx_sum, output.value)
                    self.upsert_haircut_edge(input.prev_out.id, output.id, haircut_value)

            if show_progressbar:
                progressbar.update(1)

    def populate_outputs_onebyone_getorcreate(
        self,
        session: Session,
        block_heights: list[int],
        show_progressbar=False,
        fail_if_exists=False,
        start_height: int = 0,
        skip_check_highest: bool = False
    ):

        block_heights = list(block_heights)
        block_heights.sort()

        highest_to_populate = block_heights[-1]

        if not skip_check_highest:
            highest_id = self.get_highest_vertex_id()
        else:
            highest_id = -1

        if highest_id > 0:
            highest_id = highest_id[0]
            highest_block = session.query(Block.height)\
                .join(Tx, Block.transactions)\
                .join(Output, Tx.outputs)\
                .filter(Output.id == highest_id)\
                .order_by(Block.height.desc())\
                .first().height

            if (highest_block + 1) in block_heights and fail_if_exists:
                raise ValueError(f"highest block {highest_block} is in block heights")

        if show_progressbar:
            from tqdm import tqdm
            tx_count = session.query(Tx.id)\
                              .join(Block, Tx.block)\
                              .filter(Block.height <= highest_to_populate, Block.height >= start_height)\
                              .count()
            progressbar = tqdm(total=tx_count, desc="Populating graph", unit="tx")

        tx: Tx
        for tx in self.data_provider.get_txs_for_blocks(
            session,
            min_height=start_height,
            max_height=highest_to_populate,
            buffer=2000
        ):

            tx_sum = tx.total_input_value()
            output: Output
            for output in tx.outputs:

                # Create a new output node if it doesn't exist.
                output_node = __.addV('output') \
                                .property('output_id', output.id)
                if output.address is not None:
                    output_node = output_node.property('address_id', output.address.id)

                g.V().has('output', 'output_id', output.id) \
                    .fold() \
                    .coalesce(
                        __.unfold(),
                        output_node
                ).next()

                if tx_sum == 0:
                    continue
                input: Input
                for input in tx.inputs:
                    haircut_value = haircut(input.prev_out.value, tx_sum, output.value)

                    # Connect the input node to the output node.
                    # If the edge already exists, do nothing.
                    try:
                        g.V().has('output', 'output_id', input.prev_out.id) \
                             .inE('sent').where(__.outV().has('output', 'output_id', output.id)) \
                             .fold() \
                             .coalesce(__.unfold(),
                                       __.V().has('output', 'output_id', output.id)
                                       .addE('sent')
                                       .from_(__.V().has('output', 'output_id', input.prev_out.id))
                                       .property('value', haircut_value)
                             ).next()
                    except GremlinServerError as e:
                        print(f"Error adding edge from {input.prev_out} to {output}")
                        print(f"tx: {tx.id}")
                        print(f"block: {tx.block_height}")
                        print(f"input value: {input.prev_out.value}")
                        print(f"output value: {output.value}")
                        raise e

            if show_progressbar:
                progressbar.update(1)

        if show_progressbar:
            progressbar.close()

    def create_output_nodes(
        self,
        session,
        highest_to_populate: int = None,
        lowest_to_populate: int = None,
        show_progressbar: bool = False,
        batch_size: int = 10,
        skip_check_highest: bool = False
    ):
        # TODO: Currently, this function uses all RAM and is automatically killed.
        #       This is because JanusGraph doesn't deal well with inserting
        #       a large number of vertices in batch. See https://stackoverflow.com/q/54775215/6946463
        #       We need to find a way to do this faster while using less RAM.

        if highest_to_populate is None:
            highest_to_populate = self.get_highest_block_height(session)

        if not skip_check_highest:
            highest_id = self.get_highest_vertex_id()
        else:
            highest_id = -1

        if lowest_to_populate is None:
            if highest_id < 0:
                lowest_to_populate = 0
            else:
                lowest_to_populate = session.query(Block.height)\
                    .join(Tx, Block.transactions)\
                    .join(Output, Tx.outputs)\
                    .filter(Output.id == highest_id)\
                    .order_by(Block.height.desc())\
                    .first().height

        # Get all output ids
        highest_output_id = session.query(Output.id)\
                                   .join(Tx, Output.transaction)\
                                   .filter(Tx.block_height <= highest_to_populate)\
                                   .order_by(Output.id.desc()).first()

        highest_output_id = highest_output_id[0]
        output_ids = range(highest_id + 1, highest_output_id + 1)

        if show_progressbar:
            from tqdm import tqdm
            progressbar = tqdm(output_ids, desc="Creating output nodes", unit="output")

        # Batch creation of output nodes
        batch_traversal = g
        current_chunk_count = 0
        for output in self.data_provider.get_outputs_for_blocks(
            session,
            min_height=lowest_to_populate,
            max_height=highest_to_populate,
            buffer=20_000
        ):
            if output.id not in output_ids:
                continue

            # Create a new output node if it doesn't exist.
            output_node = __.addV('output') \
                            .property('output_id', output.id)
            if output.address is not None:
                output_node = output_node.property('address_id', output.address.id)

            batch_traversal = batch_traversal.V() \
                .has('output', 'output_id', output.id) \
                .fold() \
                .coalesce(
                    __.unfold(),
                    output_node
                )

            current_chunk_count += 1

            if current_chunk_count == batch_size:
                batch_traversal.iterate()
                current_chunk_count = 0
                batch_traversal = g
                if show_progressbar:
                    progressbar.update(batch_size)

        if show_progressbar:
            progressbar.close()

    def create_haircut_edges(
        self,
        session,
        highest_to_populate: int = None,
        lowest_to_populate: int = None,
        show_progressbar: bool = False,
        batch_size: int = 10
    ):

        if highest_to_populate is None:
            highest_to_populate = self.get_highest_block_height(session)
        if lowest_to_populate is None:
            lowest_to_populate = 0

        if show_progressbar:
            # count number of transactions between 0 and highest_to_populate
            tx_count = session.query(Tx.id)\
                              .filter(Tx.block_height <= highest_to_populate, Tx.block_height >= lowest_to_populate)\
                              .count()
            from tqdm import tqdm
            progressbar = tqdm(range(0, tx_count + 1), desc="Creating haircut edges", unit="tx")

        current_batch_count = 0
        batch_traversal = g
        tx: Tx
        for tx in self.data_provider.get_txs_for_blocks(
            session,
            min_height=lowest_to_populate,
            max_height=highest_to_populate,
            buffer=20_000
        ):
            tx_sum = tx.total_input_value()
            # Some transactions send 0 BTC.
            # This is very strange, but since no value is sent,
            # no edges should be created.
            if tx_sum == 0:
                if show_progressbar:
                    progressbar.update(1)
                continue
            for output in tx.outputs:

                for input in tx.inputs:

                    haircut_value = haircut(input.prev_out.value, tx_sum, output.value)

                    batch_traversal = batch_traversal.V().has('output_id', input.prev_out.id) \
                                                            .inE('sent').where(__.outV().has('output_id', output.id)) \
                                                            .fold() \
                                                            .coalesce(__.unfold(),
                                                                    __.V().has('output_id', output.id)
                                                                        .addE('sent')
                                                                        .from_(__.V().has('output_id', input.prev_out.id))
                                                                        .property('value', haircut_value)
                                                            )

                    current_batch_count += 1
                    if current_batch_count == batch_size:
                        try:
                            batch_traversal.iterate()
                        except Exception as e:
                            print(f"Error adding edge from {input.prev_out} to {output}")
                            print(f"tx: {tx.id}")
                            print(f"block: {tx.block_height}")
                            raise e
                        current_batch_count = 0
                        batch_traversal = g

            if show_progressbar:
                progressbar.update(1)

        if show_progressbar:
            progressbar.close()

    def populate_batch(
        self,
        session: Session,
        block_heights: list[int] = None,
        show_progressbar=False,
        batch_size: int = 5,
        skip_vertices: bool = False,
        max_height: int = None,
        start_height: int = 0,
        skip_check_highest: bool = False
    ):

        if block_heights is None:
            if max_height is None:
                max_height = self.get_highest_block_height(session) + 1
            block_heights = list(range(start_height, max_height))

        else:
            block_heights = list(block_heights)
            block_heights.sort()

        lowest_to_populate = block_heights[0]
        highest_to_populate = block_heights[-1]

        # First, create all vertices
        if not skip_vertices:
            self.create_output_nodes(session,
                                     highest_to_populate,
                                     lowest_to_populate,
                                     show_progressbar,
                                     batch_size,
                                     skip_check_highest=skip_check_highest)

        # Then, create all "sent" edges
        self.create_haircut_edges(session, highest_to_populate, lowest_to_populate, show_progressbar, batch_size)

        print("Done.")


if __name__ == '__main__':
    import argparse

    from models.base import SessionLocal
    from blockchain_data_provider import PersistentBlockchainAPIData

    parser = argparse.ArgumentParser(description="Script for populating database")
    parser.add_argument('--height', default=None, type=int, help='Block height up to which to populate')
    parser.add_argument('--delete', default=False, action='store_true',
                        help='Delete all data in database and don\'t populate.')

    parser.add_argument('--batch', default=False, action='store_true',
                        help='Batch populate graph.')
    parser.add_argument('--skip-vertices', default=False, action='store_true',
                        help='Skip creating vertices during batch population. Only create edges.')

    parser.add_argument('--start-height', default=0, type=int, dest='start_height',
                        help='Block height to start populating from')
    # Why is this check unbearably long?
    # See https://stackoverflow.com/questions/70697793/faster-janusgraph-queries
    # And also https://stackoverflow.com/questions/62480262/gremlin-haslabel-query-times-out
    parser.add_argument('--skip-check-highest', default=False, action='store_true',
                        dest='skip_check_highest',
                        help='Skip checking highest output node id in database. Sometimes'
                        'This check can be unbearably long ')

    args = parser.parse_args()

    data_provider = PersistentBlockchainAPIData()

    populator = PopulateOutputProportionGraph(data_provider)

    if args.delete:
        print("Deleting all graph data...")
        # wipe the database
        populator.clear_graph()
        print("Graph data wiped.")
    else:
        with SessionLocal() as session:
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
                if args.batch:
                    print("Batch populating graph...")
                    populator.populate_batch(session,
                                             show_progressbar=True, skip_vertices=args.skip_vertices,
                                             max_height=args.height,
                                             start_height=args.start_height,
                                             skip_check_highest=args.skip_check_highest)
                else:
                    if args.skip_vertices:
                        raise ValueError("This argument cannot be used without --batch")
                    populator.populate_outputs_onebyone_getorcreate(
                        session,
                        range(0, highest_block.height + 1),
                        show_progressbar=True,
                        start_height=args.start_height,
                        skip_check_highest=args.skip_check_highest
                    )
