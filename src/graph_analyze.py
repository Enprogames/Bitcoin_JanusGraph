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
            vertex_id: The ID of the vertex (output or address) to start the traversal.
            vertex_type: The type of ID being provided ('output' or 'address').

        Returns:
            Gremlin traversal of the history of the specified vertex.
        """
        assert vertex_type in ['output', 'address'], "vertex_type must be 'output' or 'address'"

        # Start the traversal at the specified vertex or vertices
        if vertex_type == 'output':
            vertex_traversal = self.g.V().has('id', vertex_id)
        elif vertex_type == 'address':
            vertex_traversal = self.g.V().has('address', vertex_id)

        # Collect history by traversing sent edges backwards
        history = vertex_traversal.repeat(
            __.in_('sent')
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

        return self.get_vertex_history(address.id, 'address')

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
        results = subgraph_traversal.project('vertex', 'edges').by(__.elementMap()).by(__.bothE().elementMap().fold()).toList()

        nx_graph = nx.DiGraph()

        # Add vertices and edges to the NetworkX graph
        for item in results:
            vertex_properties = item['vertex']

            nx_graph.add_node(vertex_properties[T.id], output_id=vertex_properties['id'], label=vertex_properties[T.label])

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
