import networkx as nx
from ipycytoscape import CytoscapeWidget


# Create visualizations
def visualize_graph(G, layout: str = 'cola', node_color_map: dict = {}, edge_style_lambda=None):
    cyto_graph = CytoscapeWidget()
    cyto_graph.graph.add_graph_from_networkx(G, directed=isinstance(G, nx.DiGraph))
    cyto_graph.wheel_sensitivity = 0.2

    # Create a color map for nodes in the same component
    colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'cyan']

    default_vertex_style = {
        'label': 'data(id)',
        'background-color': 'grey',
        'color': 'grey',
        'width': 20
    }

    # Apply node colors based on components
    for node in cyto_graph.graph.nodes:
        node.data['color'] = node_color_map.get(int(node.data['id']), 'grey')

    # Default edge style
    default_edge_style = {
        "curve_style": "bezier",
        "target_arrow_shape": "triangle",
        "target_arrow_color": "#9dbaea",
        "line_color": "#9dbaea",
        "line_style": "solid",
    }

    # Apply custom styles to edges
    for edge in cyto_graph.graph.edges:
        edge_tuple = (int(edge.data['source']), int(edge.data['target']))
        custom_style = edge_style_lambda(edge_tuple) if edge_style_lambda else {}
        for key, value in default_edge_style.items():
            edge.data[key] = custom_style.get(key, value)

    # Apply styles
    cyto_graph.set_style([
        {
            'selector': 'node',
            'style': {
                'background-color': 'data(color)',
                # 'label': 'data(id)'
                'label': 'data(pretty_label)'
            },
        },
        {
            "selector": "edge.directed",
            "style": {
                "curve-style": "data(curve_style)",
                "target-arrow-shape": "data(target_arrow_shape)",
                "target-arrow-color": "data(target_arrow_color)",
                "line-color": "data(line_color)",
                "line-style": "data(line_style)",
                "label": "data(pretty_label)",
                # "target_arrow_shape": 'triangle',
                # "target_arrow_color": "#9dbaea",
                # "curve-style": "bezier",
                # "line-style": "dashed",
                # "line-color": "#9dbaea",
            },
        }
    ])

    cyto_graph.set_layout(name=layout, nodeDimensionsIncludeLabels=True, rankDir='LR')

    return cyto_graph
