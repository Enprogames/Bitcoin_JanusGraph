:remote connect tinkerpop.server conf/remote.yaml session
:remote console

:> mgmt = graph.openManagement(); mgmt.printSchema();
