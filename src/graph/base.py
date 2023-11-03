import os
from importlib.metadata import version

from dotenv import load_dotenv

import gremlin_python

# from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python import statics
from gremlin_python.structure.graph import Graph
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection


statics.load_statics(globals())


load_dotenv()

GRAPH_DB_HOST = os.getenv("GRAPH_DB_HOST")
GRAPH_DB_USER = os.getenv("GRAPH_DB_USER")
GRAPH_DB_PASSWORD = os.getenv("GRAPH_DB_PASSWORD")
GREMLIN_SEVER_PORT = os.getenv("GREMLIN_SEVER_PORT")
GRAPH_DB_URL = f"ws://{GRAPH_DB_HOST}:{GREMLIN_SEVER_PORT}/gremlin"

assert GRAPH_DB_HOST is not None and GREMLIN_SEVER_PORT is not None and GRAPH_DB_USER is not None \
    and GRAPH_DB_PASSWORD is not None, \
    "GRAPH_DB_HOST, GREMLIN_DB_USER, GREMLIN_DB_PASSWORD, and GREMLIN_SEVER_PORT must be set in .env file"
gremlin_version = tuple([int(x) for x in version('gremlinpython').split('.')])
if (gremlin_version <= (3, 4, 0)):
    graph = Graph()
    g = graph.traversal().withRemote(DriverRemoteConnection(GRAPH_DB_URL, 'g'))
else:
    from gremlin_python.process.anonymous_traversal import traversal
    g = traversal().withRemote(DriverRemoteConnection(GRAPH_DB_URL, 'g',
                                                      username=GRAPH_DB_USER, password=GRAPH_DB_PASSWORD))

print(GRAPH_DB_URL)
