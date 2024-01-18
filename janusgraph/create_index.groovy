// ./janusgraph/create_index.groovy
:remote connect tinkerpop.server conf/remote.yaml
:remote console

// create sent edge label if it doens't exist
// create property 'value' if it doesn't exist
// value = mgmt.containsPropertyKey('value') ? mgmt.getPropertyKey('value') : mgmt.makePropertyKey('value').dataType(Double.class).make();


// create vertex property 'owner_id' if it doesn't exist
// create vertex property 'output_id' if it doesn't exist
// create vertex property 'address_id' if it doesn't exist
// create composite index on vertex property 'output_id' if it doesn't exist
// create composite index on vertex property 'address_id' if it doesn't exist
// create composite index on vertex property 'owner_id' if it doesn't exist

:> graph.tx().rollback(); mgmt = graph.openManagement(); idKey = mgmt.containsPropertyKey('output_id') ? mgmt.getPropertyKey('output_id') : mgmt.makePropertyKey('output_id').dataType(Integer.class).make(); addressKey = mgmt.containsPropertyKey('address_id') ? mgmt.getPropertyKey('address_id') : mgmt.makePropertyKey('address_id').dataType(Integer.class).make(); if (!mgmt.containsGraphIndex('byOutputIdComposite')) { mgmt.buildIndex('byOutputIdComposite', Vertex.class).addKey(idKey).buildCompositeIndex(); }; if (!mgmt.containsGraphIndex('byAddressIdComposite')) { mgmt.buildIndex('byAddressIdComposite', Vertex.class).addKey(addressKey).buildCompositeIndex(); }; ownerId = mgmt.containsPropertyKey('owner_id') ? mgmt.getPropertyKey('owner_id') : mgmt.makePropertyKey('owner_id').dataType(Integer.class).make(); sent = mgmt.containsEdgeLabel('sent') ? mgmt.getEdgeLabel('sent') : mgmt.makeEdgeLabel('sent').multiplicity(SIMPLE).make(); if (!mgmt.containsGraphIndex('byOwnerIdComposite')) { mgmt.buildIndex('byOwnerIdComposite', Vertex.class).addKey(ownerId).buildCompositeIndex(); }; mgmt.commit();

