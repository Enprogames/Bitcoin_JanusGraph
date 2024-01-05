
:remote connect tinkerpop.server conf/remote.yaml
:remote console

:> graph.tx().rollback(); mgmt = graph.openManagement(); idKey = mgmt.containsPropertyKey('output_id') ? mgmt.getPropertyKey('output_id') : mgmt.makePropertyKey('output_id').dataType(Integer.class).make(); addressKey = mgmt.containsPropertyKey('address_id') ? mgmt.getPropertyKey('address_id') : mgmt.makePropertyKey('address_id').dataType(Integer.class).make(); if (!mgmt.containsGraphIndex('byOutputIdComposite')) { mgmt.buildIndex('byOutputIdComposite', Vertex.class).addKey(idKey).buildCompositeIndex(); }; if (!mgmt.containsGraphIndex('byAddressIdComposite')) { mgmt.buildIndex('byAddressIdComposite', Vertex.class).addKey(addressKey).buildCompositeIndex(); }; mgmt.commit();
