import networkx as nx
from gremlin_python.process.graph_traversal import GraphTraversalSource

from graph.base import g


class GraphAnalyzer:
    def __init__(self):
        pass

    def to_networkx(self, subgraph_traversal) -> nx.DiGraph:
        """Given a gremlin-python graph traversal, specifying a subgraph, return a networkx graph.
        """
        # Create a NetworkX graph (directed or undirected based on your graph's nature)
        nx_graph = nx.DiGraph()  # Use nx.Graph() for an undirected graph

        # Execute the traversal to get the subgraph vertices and edges
        vertices = subgraph_traversal.toSet()
        edges = subgraph_traversal.bothE().toList()

        # Add vertices to the NetworkX graph
        for vertex in vertices:
            properties = {prop.key: prop.value for prop in vertex.properties()}
            nx_graph.add_node(vertex.id, **properties)

        # Add edges to the NetworkX graph
        for edge in edges:
            properties = {prop.key: prop.value for prop in edge.properties()}
            nx_graph.add_edge(edge.outV.id, edge.inV.id, **properties)

        return nx_graph
