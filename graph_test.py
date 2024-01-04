import sys
from pathlib import Path

container_src_path = Path('/app/src/')
local_src_path = Path(Path.cwd(), 'src/')

# see if this src path exists.
# if it does, we are in a container.
# if not, we are in local.
if not container_src_path.exists():
    src_path = local_src_path
else:
    src_path = container_src_path

src_path_str = str(src_path)
if src_path_str not in sys.path:
    sys.path.insert(0, src_path_str)

from dotenv import load_dotenv

from graph.base import g

from gremlin_python import statics
from gremlin_python.process.traversal import T
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.strategies import *
from gremlin_python.process.graph_traversal import GraphTraversalSource


# clear database
# g.V().drop().iterate()

pass

exit()

# add vertices
# CUSTOM VERTEX ID DOESN'T WORK
# g.addV('person').property(T.id, 2).property('name', 'Sal').property('marked', True).next()
g.addV('person').property('name', 'Sal').property('marked', True).next()
g.addV('person').property('name', 'Rob').property('marked', True).next()
g.addV('person').property('name', 'Frank').next()
g.addV('person').property('name', 'Sally').next()
g.addV('person').property('name', 'Bill').property('marked', True).next()
g.addV('person').property('name', 'Bob').next()
g.addV('person').property('name', 'John').next()

# add edges
g.V().has('name', 'Sal').addE('sent').to(__.V().has('name', 'Rob')).property('value', 17).next()
g.V().has('name', 'Rob').addE('sent').to(__.V().has('name', 'Frank')).property('value', 8).next()
g.V().has('name', 'Rob').addE('sent').to(__.V().has('name', 'Sally')).property('value', 7).next()
g.V().has('name', 'Bill').addE('sent').to(__.V().has('name', 'Frank')).property('value', 3).next()
g.V().has('name', 'Bill').addE('sent').to(__.V().has('name', 'Sally')).property('value', 10).next()
g.V().has('name', 'Frank').addE('sent').to(__.V().has('name', 'Bob')).property('value', 5).next()
g.V().has('name', 'Frank').addE('sent').to(__.V().has('name', 'John')).property('value', 2).next()
g.V().has('name', 'Sally').addE('sent').to(__.V().has('name', 'Bob')).property('value', 3).next()
g.V().has('name', 'Sally').addE('sent').to(__.V().has('name', 'John')).property('value', 3).next()

edge = g.V().has('name', 'Rob').outE('sent').next()
print(edge)
print(f"edge id: {edge.id['@value']['relationId']}")
print(g.V().has('name', 'Rob').outE('sent').as_('e').inV().has('name', 'Frank').select('e').valueMap().toList())


def get_sources(g: GraphTraversalSource, node_name):
    source_record = {}

    def traverse_sources(vertex, fraction=1.0):
        # Traverse incoming edges
        in_edges = g.V(vertex).inE('sent').toList()
        for edge in in_edges:
            # sender = edge.outV().next()
            sender = g.E(edge.id['@value']['relationId']).outV().next()
            amount_from_sender = g.E(edge.id['@value']['relationId']).values('value').next()
            if True in g.V(sender).values('marked').toList():
                name = g.V(sender).values('name').next()
                # Add record if sender is marked
                if name in source_record:
                    source_record[name] += amount_from_sender * fraction
                else:
                    source_record[name] = amount_from_sender * fraction
            # Recursive case
            if g.V(sender).inE('sent').hasNext():
                sender_total_received = sum(sent_value for sent_value in g.V(sender).inE('sent').values('value').toList())
                amount_fraction = (amount_from_sender / sender_total_received) * fraction
                traverse_sources(sender, amount_fraction)

    # Start traversal
    traverse_sources(g.V().has('name', node_name).next())
    return source_record


print("Sources for Bob:")
print(get_sources(g, 'Bob'))
