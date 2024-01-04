import os
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

# clear database
print("Clearing vertices")
if g.V().count().next() > 0:
    g.V().drop().iterate()
    print("All vertices cleared.")

vertices_to_add = 2_000_000
chunk_size = 100

chunk_count = 0
my_traversal = g
progress_bar = tqdm(total=(vertices_to_add // chunk_size) + 1)
progress_bar.set_description("Adding vertices")

# add vertices in chunks of size chunk_size
for i in range(vertices_to_add):
    my_traversal = my_traversal.addV('person').property('id', i)

    chunk_count += 1

    if chunk_count == chunk_size:
        my_traversal.iterate()
        my_traversal = g
        chunk_count = 0
        progress_bar.update(1)

# add any remaining vertices
if chunk_count > 0:
    my_traversal.iterate()

progress_bar.close()

# clear database
print("Clearing vertices")
if g.V().count().next() > 0:
    g.V().drop().iterate()
    print("All vertices cleared.")
