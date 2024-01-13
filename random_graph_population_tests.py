import os
import random
from tqdm import tqdm
from dotenv import load_dotenv

from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __, GraphTraversalSource
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection


load_dotenv()

GRAPH_DB_HOST = os.getenv("GRAPH_DB_HOST")
GRAPH_DB_USER = os.getenv("GRAPH_DB_USER")
GRAPH_DB_PASSWORD = os.getenv("GRAPH_DB_PASSWORD")
GREMLIN_SEVER_PORT = os.getenv("GREMLIN_SEVER_PORT")
GRAPH_DB_URL = f"ws://{GRAPH_DB_HOST}:{GREMLIN_SEVER_PORT}/gremlin"


g: GraphTraversalSource = traversal().withRemote(
    DriverRemoteConnection(GRAPH_DB_URL, 'g',
                           username=GRAPH_DB_USER,
                           password=GRAPH_DB_PASSWORD)
)

vertices_to_add = 10_000_000

my_traversal = g
progress_bar = tqdm(total=vertices_to_add)
progress_bar.set_description("Adding vertices")

# add vertices in chunks of size chunk_size
for i in range(vertices_to_add):
    g.V().has('person', 'output_id', i) \
        .fold() \
        .coalesce(
        __.unfold(),
        __.addV('person').property('output_id', i)
    ).next()

    # create vertices from the last 10 people
    if i > 10:
        for j in range(1, 11):
            g.V().has('person', 'output_id', i - j) \
                 .inE('my_edge').where(__.outV().has('person', 'output_id', i)) \
                 .fold() \
                 .coalesce(__.unfold(),
                           __.V().has('person', 'output_id', i)
                           .addE('my_edge')
                           .from_(__.V().has('person', 'output_id', i - j))
                           .property('value', random.randint(1, 1000))
                           ).next()

    progress_bar.update(1)

progress_bar.close()
