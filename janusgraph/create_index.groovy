
:remote connect tinkerpop.server conf/remote.yaml
:remote console

:> graph.tx().rollback(); mgmt = graph.openManagement(); idKey = mgmt.containsPropertyKey('id') ? mgmt.getPropertyKey('id') : mgmt.makePropertyKey('id').dataType(Integer.class).make(); addressKey = mgmt.containsPropertyKey('address') ? mgmt.getPropertyKey('address') : mgmt.makePropertyKey('address').dataType(Integer.class).make(); if (!mgmt.containsGraphIndex('byIdComposite')) { mgmt.buildIndex('byIdComposite', Vertex.class).addKey(idKey).buildCompositeIndex(); }; if (!mgmt.containsGraphIndex('byAddressComposite')) { mgmt.buildIndex('byAddressComposite', Vertex.class).addKey(addressKey).buildCompositeIndex(); }; mgmt.commit();
