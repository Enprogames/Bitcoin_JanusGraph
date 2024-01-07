# TODO
## Blockchain Database Population
- [x] Get simple blockchain data populated
- [x] Deal with duplicate transactions; set `is_duplicate` value when a duplicate transaction is found.
- [x] Populate `Address`es.
- [x] `prev_out` finding error on block 2,812.
- [x] Deal with zero-valued transactions.
- [x] Create some simple unit tests to validate the integrity of a few key data items in the populated database.
    - [x] Ensuring duplicate transactions are marked as such.
    - [x] Retrieving previous outputs from inputs.
    - [x] Retrieving all outputs for an address.
## Graph Database Population
- [x] Create `PopulateOutputProportionGraph` class to populate graph database.
- [x] Implement tracing algorithm for graph database.
- [ ] Create some simple unit tests to validate the integrity of a few key data items in the populated database.
    - [ ] Ensuring duplicate transactions are marked as such.
    - [ ] Retrieving previous outputs from inputs.
    - [ ] Retrieving all outputs for an address.
- [x] Visualize some interesting data.
    - [x] Find some interesting transactions.

## Paper
- [ ] Literature Review
    - [ ] Address Clustering using Heuristics and Algorithms
    - [ ] 
    - [ ] **Algorithms used by Taintchain
    - [ ] ** Algorithms used by BitIondine
- [ ] Consistent definition of tracing
    - [ ] Different definitions by different researchers
    - [ ] My definition
- [ ] Data Preparation
    - [ ] Duplicate Transactions

## Ideas and Notes
#### Frequency Distribution of Transactions within Blocks
<!-- TODO: -->
```sql
WITH MaxHeight AS (
    SELECT MAX(height) as max_height FROM blocks
),
HeightRanges AS (
    SELECT
        FLOOR(height / :increment) * :increment AS RangeStart,
        LEAST(FLOOR(height / :increment) * :increment + :increment - 1, (SELECT max_height FROM MaxHeight)) AS RangeEnd
    FROM
        blocks
    GROUP BY RangeStart
)
SELECT
    RangeStart,
    RangeEnd,
    COUNT(transactions.id) AS TransactionCount
FROM
    HeightRanges
LEFT JOIN
    transactions ON transactions.block_height >= HeightRanges.RangeStart AND transactions.block_height <= HeightRanges.RangeEnd
GROUP BY
    RangeStart, RangeEnd
ORDER BY
    RangeStart;
```

Some results:
```
rangestart|rangeend|transactioncount|
----------+--------+----------------+
       0.0|  9999.0|           10092|
   10000.0| 19999.0|           10044|
   20000.0| 29999.0|           10076|
   30000.0| 39999.0|           10125|
   40000.0| 49999.0|           10442|
   50000.0| 59999.0|           15602|
   60000.0| 69999.0|           23723|
   70000.0| 79999.0|           25047|
   80000.0| 89999.0|           24329|
   90000.0| 99999.0|           77093|
  100000.0|109999.0|           73081|
  110000.0|119999.0|          145826|
  120000.0|129999.0|          255577|
  130000.0|138146.0|          446362|
```

#### Very Strange Transactions
Block [168,710](https://blockchain.info/rawblock/168710) has a coinbase transaction with several outputs ([369970d60ba54bae122be472366938626d2533e2f79cdda407e48eaa3765c68a](https://blockchain.info/rawtx/369970d60ba54bae122be472366938626d2533e2f79cdda407e48eaa3765c68a)). Additionally, several of the outputs have values of 0. This is not incredibly strange by itself, but later, these outputs are spent with a value of 0. The transaction is [3a5e0977cc64e601490a761d83a4ea5be3cd03b0ffb73f5fe8be6507539be76c](https://blockchain.info/rawtx/3a5e0977cc64e601490a761d83a4ea5be3cd03b0ffb73f5fe8be6507539be76c).

Since no value is being transferred, I have decided to not include edges between these transaction outputs in the graph.

The original error I received is shown below:
```
Error adding edge from <Output(id=5830335)> to <Output(id=5852639)>
tx: 2519056
block: 168910
Traceback (most recent call last):
  File "/home/yellow_bright612/Dropbox/VSCodeProjects/Bitcoin/bitcoin_janusgraph/src/graph_populate.py", line 359, in <module>
    populator.populate_batch(session, range(0, highest_block.height + 1), show_progressbar=True)
  File "/home/yellow_bright612/Dropbox/VSCodeProjects/Bitcoin/bitcoin_janusgraph/src/graph_populate.py", line 311, in populate_batch
    self.create_haircut_edges(session, highest_to_populate, show_progressbar, batch_size)
  File "/home/yellow_bright612/Dropbox/VSCodeProjects/Bitcoin/bitcoin_janusgraph/src/graph_populate.py", line 281, in create_haircut_edges
    raise e
  File "/home/yellow_bright612/Dropbox/VSCodeProjects/Bitcoin/bitcoin_janusgraph/src/graph_populate.py", line 256, in create_haircut_edges
    haircut_value = haircut(input.prev_out.value, tx_sum, output.value)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/yellow_bright612/Dropbox/VSCodeProjects/Bitcoin/bitcoin_janusgraph/src/graph_populate.py", line 25, in haircut
    return (input_value / sum_of_inputs) * output_value
            ~~~~~~~~~~~~^~~~~~~~~~~~~~~
ZeroDivisionError: division by zero
```
