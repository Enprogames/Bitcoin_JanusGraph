# TODO
## Blockchain Database Population
- [x] Get simple blockchain data populated
- [x] Deal with duplicate transactions; set `is_duplicate` value when a duplicate transaction is found.
- [x] Populate `Address`'s.
- [x] `prev_out` finding error on block 2,812.
- [ ] Create some simple unit tests to validate the integrity of a few key data items in the populated database.
    - [ ] Ensuring duplicate transactions are marked as such.
    - [ ] Retrieving previous outputs from inputs.
    - [ ] Retrieving all outputs for an address.
## Graph Database Population
- [ ] Create `PopulateOutputProportionGraph` class to populate graph database.
- [ ] Implement tracing algorithm in Gremlin query language.
