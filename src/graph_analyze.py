import networkx as nx
from sqlalchemy.orm import joinedload
from gremlin_python import statics
from gremlin_python.process.traversal import T, Direction
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.graph_traversal import GraphTraversalSource

from models.base import SessionLocal
from models.bitcoin_data import Block, Tx, Address, Input, Output, BITCOIN_TO_SATOSHI
from graph.base import g


class GraphAnalyzer:
    def __init__(self, g: GraphTraversalSource, sqlalchemy_session_factory: SessionLocal):
        self.g = g
        self.sqlalchemy_session_factory = sqlalchemy_session_factory

    def get_vertex_history(self, vertex_id: int, vertex_type: str):
        """
        Retrieve the entire history of transactions for a given output or address.

        Args:
            vertex_id: The ID of the vertex (output or address) to start the traversal.
            vertex_type: The type of ID being provided ('output' or 'address').

        Returns:
            Gremlin traversal of the history of the specified vertex.
        """
        assert vertex_type in ['output', 'address'], "vertex_type must be 'output' or 'address'"

        # Start the traversal at the specified vertex or vertices
        if vertex_type == 'output':
            vertex_traversal = self.g.V().has('output_id', vertex_id)
        elif vertex_type == 'address':
            vertex_traversal = self.g.V().has('address_id', vertex_id)

        # Collect history by traversing sent edges backwards
        history = vertex_traversal.repeat(
            __.inE('sent').otherV()
        ).emit()

        return history
    
    def get_vertex_path(self, vertex_id: int, vertex_type: str):
        """
        Retrieve the paths going forward from a given output or address.

        Args:
            vertex_id: The ID of the vertex (output or address) to start the traversal.
            vertex_type: The type of ID being provided ('output' or 'address').
=
        Returns:
            Gremlin traversal of the paths of the specified vertex.
        """
        assert vertex_type in ['output', 'address'], "vertex_type must be 'output' or 'address'"

        # Start the traversal at the specified vertex or vertices
        if vertex_type == 'output':
            vertex_traversal = self.g.V().has('output_id', vertex_id)
        elif vertex_type == 'address':
            vertex_traversal = self.g.V().has('address_id', vertex_id)

        history = vertex_traversal.repeat(
            __.outE('sent').otherV()
        ).emit()

        return history

    def get_address_history(self, address_str: str):
        """
        Retrieve the entire history of transactions for a given address.

        Args:
            address_str: The address to start the traversal.

        Returns:
            Gremlin traversal of the history of the specified address.
        """
        with self.sqlalchemy_session_factory() as session:
            address = session.query(Address).filter_by(addr=address_str).first()

        if not address:
            raise ValueError(f"address {address_str} not found")

        return self.get_vertex_history(address.id, 'address')

    def get_output_history(self, output_id: int):
        """
        Retrieve the entire history of transactions for a given output.

        Args:
            output_id: The ID of the output to start the traversal.

        Returns:
            Gremlin traversal of the history of the specified output.
        """
        with self.sqlalchemy_session_factory() as session:
            output = session.query(Output).filter_by(id=output_id).first()

        if not output:
            raise ValueError(f"output {output_id} not found")

        return self.get_vertex_history(output.id, 'output')

    def traversal_to_networkx(
        self,
        subgraph_traversal,
        limit=10_000,
        include_data: bool = False
    ) -> nx.DiGraph:
        """Given a gremlin-python graph traversal, specifying a subgraph, return a networkx graph.

        Args:
            subgraph_traversal: Gremlin-python graph traversal specifying a subgraph.
            limit: The maximum number of vertices to return.
            include_data: Whether to include all data from the database in the graph.
                          For example, block height, full addresses, etc.

        Returns:
            A networkx graph.
        """
        # get the vertices and edges from the traversal
        # results = subgraph_traversal.project('vertex', 'edges')\
        #                             .by(__.elementMap())\
        #                             .by(__.bothE().elementMap().fold())\
        #                             .toList()
        results = subgraph_traversal.path()\
                                    .by(__.elementMap())\
                                    .by(__.elementMap())\
                                    .unfold()\
                                    .toList()

        nx_graph = nx.DiGraph()
        vertex_items = [item for item in results if item[T.label] == 'output']
        edge_items = [item for item in results if item[T.label] == 'sent']

        # Add vertices and edges to the NetworkX graph
        for vertex_properties in vertex_items:

            nx_graph.add_node(
                int(vertex_properties[T.id]),
                output_id=int(vertex_properties['output_id']),
                label=vertex_properties[T.label]
            )

            if 'address_id' in vertex_properties:
                address_id = int(vertex_properties['address_id'])
            else:
                address_id = None

            nx_graph.nodes[vertex_properties[T.id]].update({'address_id': int(address_id)})

        for edge_properties in edge_items:
            in_node = edge_properties[Direction.IN]
            out_node = edge_properties[Direction.OUT]
            if nx_graph.has_node(in_node[T.id]) and nx_graph.has_node(out_node[T.id]):
                nx_graph.add_edge(out_node[T.id], in_node[T.id], label=edge_properties[T.label])
                if edge_properties[T.label] == 'sent':
                    nx_graph.edges[out_node[T.id], in_node[T.id]].update({'value': float(edge_properties['value'])})

        if include_data:
            output_ids = [data['output_id'] for id_, data in nx_graph.nodes.data()]
            with self.sqlalchemy_session_factory() as session:
                outputs = session.query(Output)\
                                 .filter(Output.id.in_(output_ids))\
                                 .options(
                                     joinedload(Output.transaction),
                                     joinedload(Output.address)
                                 ).all()

            output_dict = {output.id: output for output in outputs}

            for id_, data in nx_graph.nodes(data=True):
                output = output_dict[data['output_id']]
                data.update({
                    'block_height': output.transaction.block_height,
                    'tx_index_in_block': output.transaction.index_in_block,
                    'index_in_tx': output.index_in_tx,
                    'value': output.value,
                    'address': output.address.addr,
                    'pretty_label': output.pretty_label()
                })

            for u, v in nx_graph.edges():
                nx_graph.edges[u, v]['pretty_label'] = f"{round(nx_graph.edges[u, v]['value'] / BITCOIN_TO_SATOSHI, 10)}"

        return nx_graph

    def get_coin_sources(
        self,
        vertex_id: int,
        vertex_type: str,
        graph: nx.DiGraph,
        pretty_labels: bool = False
    ):

        assert vertex_type in ['output', 'address'], "vertex_type must be 'output' or 'address'"

        sources_record = {}

        def traverse_sources(vertex, fraction=1.0):
            # Traverse incoming edges
            for sender in graph.successors(vertex):
                amount_from_sender = graph.edges[vertex, sender]['value']
                sender_output_id = graph.nodes[sender]['output_id']

                # Add record for this sender
                if sender_output_id in sources_record:
                    sources_record[sender_output_id] += amount_from_sender * fraction
                else:
                    sources_record[sender_output_id] = amount_from_sender * fraction
                # Recursive case
                predecessors = graph.successors(sender)
                if predecessors:
                    sender_total_received = sum([graph[sender][pred]['value'] for pred in predecessors])
                    if sender_total_received > 0:
                        amount_fraction = (amount_from_sender / sender_total_received) * fraction
                        traverse_sources(sender, amount_fraction)

        # find vertices with given id
        vertices = []
        total_contribution = 0
        for node, data in graph.nodes(data=True):
            if vertex_type == 'output' and 'output_id' in data and data['output_id'] == vertex_id:
                vertices.append(node)
                total_contribution += graph.nodes[node]['value']
            elif vertex_type == 'address' and 'address_id' in data and data['address_id'] == vertex_id:
                vertices.append(node)
                total_contribution += graph.nodes[node]['value']

        assert vertices, f"No vertices of type '{vertex_type}' with id {vertex_id} found"
        # Start traversal
        graph = graph.reverse()
        try:
            for vertex in vertices:
                if graph.nodes[vertex]['value'] > 0:
                    traverse_sources(vertex, fraction=graph.nodes[vertex]['value'] / total_contribution)
        finally:
            graph = graph.reverse()

        if pretty_labels:
            with self.sqlalchemy_session_factory() as session:
                outputs = session.query(Output)\
                                 .filter(Output.id.in_(sources_record.keys()))\
                                 .options(
                                     joinedload(Output.transaction),
                                     joinedload(Output.address)
                                 )\
                                 .all()
            output_dict = {output.id: output for output in outputs}

            for output_id, amount in sources_record.items():
                sources_record[output_id] = {
                    'amount': amount / BITCOIN_TO_SATOSHI,
                    'label': output_dict[output_id].pretty_label()
                }
        return sources_record
    
    def get_coin_destinations(
        self,
        vertex_id: int,
        vertex_type: str,
        graph: nx.DiGraph,
        pretty_labels: bool = False
    ):
        pass


if __name__ == '__main__':
    # Create a graph analyzer
    analyzer = GraphAnalyzer(g, SessionLocal)

    interesting_addr = '1BBz9Z15YpELQ4QP5sEKb1SwxkcmPb5TMs'

    with SessionLocal() as session:
        address = session.query(Address).filter_by(addr=interesting_addr).first()

    if not address:
        print(f"address {interesting_addr} not found")
        exit(1)

    print(f"id of address {address.addr:4}: {address.id}")

    # Get the history of a given address
    my_hist = analyzer.get_address_history(interesting_addr)
    graph = analyzer.traversal_to_networkx(my_hist, include_data=True)
