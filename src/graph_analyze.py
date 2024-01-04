import networkx as nx
from gremlin_python import statics
from gremlin_python.process.traversal import T, Direction
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.graph_traversal import GraphTraversalSource

from models.base import SessionLocal
from models.bitcoin_data import Block, Tx, Address, Input, Output
from graph.base import g


class GraphAnalyzer:
    def __init__(self, g: GraphTraversalSource, sqlalchemy_session_factory: SessionLocal):
        self.g = g
        self.sqlalchemy_session_factory = sqlalchemy_session_factory

    def get_vertex_history(self, vertex_id: int, vertex_type: str):
        """
        Retrieve the entire history of transactions for a given output or address.

        Args:
            g: The Gremlin traversal source.
            vertex_id: The ID of the vertex (output or address) to start the traversal.
            vertex_type: The type (label) of the vertex ('output' or 'address').

        Returns:
            A list of transactions in the history of the specified node.
        """
        assert vertex_id in ['output', 'address'], "vertex_id must be 'output' or 'address'"

        # Start the traversal at the specified vertex
        vertex_traversal = self.g.V().has(vertex_type, 'id', vertex_id)

        # If the starting point is an address, navigate to its associated outputs
        if vertex_type == 'address':
            vertex_traversal = vertex_traversal.in_('has_address')

        # Collect history by traversing sent edges backwards
        history = vertex_traversal.repeat(
            __.in_('sent')
        ).emit().dedup()

        return history

    def get_address_history(self, address_str: str):
        """
        Retrieve the entire history of transactions for a given address.

        Args:
            g: The Gremlin traversal source.
            address_str: The address to start the traversal.

        Returns:
            A list of transactions in the history of the specified address.
        """
        with self.sqlalchemy_session_factory() as session:
            address = session.query(Address).filter_by(addr=address_str).first()

        return self.get_vertex_history(address.id, 'address')

    def traversal_to_networkx(self, subgraph_traversal, limit=10_000, include_data: bool = False) -> nx.DiGraph:
        """Given a gremlin-python graph traversal, specifying a subgraph, return a networkx graph.
        """
        # get the vertices and edges from the traversal
        results = subgraph_traversal.project('vertex', 'edges').by(__.elementMap()).by(__.bothE().elementMap().fold()).toList()

        nx_graph = nx.DiGraph()

        # Add vertices and edges to the NetworkX graph
        for item in results:
            vertex_properties = item['vertex']

            nx_graph.add_node(vertex_properties[T.id], btc_id=vertex_properties['id'], label=vertex_properties[T.label])

            for edge in item['edges']:
                in_node = edge[Direction.IN]
                out_node = edge[Direction.OUT]
                nx_graph.add_edge(out_node[T.id], in_node[T.id], label=edge[T.label])
                if edge[T.label] == 'sent':
                    nx_graph.edges[out_node[T.id], in_node[T.id]].update({'value': edge['value']})
                    
        if include_data:
            pass
            # TODO: Query database to add all data to graph vertices

        return nx_graph
