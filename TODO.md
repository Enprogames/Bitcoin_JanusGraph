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
- [ ] Implement "address" tracing algorithm which respects outputs that have been spent.
- [ ] Create some simple unit tests to validate the integrity of a few key data items in the populated database.
    - [x] Ensuring duplicate transactions are marked as such.
    - [x] Retrieving previous outputs from inputs.
    - [x] Retrieving all outputs for an address.
- [x] Visualize some interesting data.
    - [x] Find some interesting transactions.
    - [ ] Can I improve performance of "n-hop" subgraph visualization?

## Paper
- [x] Literature Review
    - [x] Address Clustering using Heuristics and Algorithms
    <!-- - [ ] **Algorithms used by Taintchain
    - [ ] ** Algorithms used by BitIondine -->
<!-- - [ ] Consistent definition of tracing
    - [ ] Different definitions by different researchers
    - [ ] My definition -->
- [x] Data Preparation
    - [x] Duplicate Transactions
    - [x] Invalid transactions
    - [ ] Zero-valued transactions

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
        LEAST(FLOOR(height / :increment) * :increment + :increment - 1, (SELECT max_height FROM MaxHeight)) AS RangeEnd,
        COUNT(*) AS BlockCount -- Counting blocks in each range
    FROM
        blocks
    GROUP BY RangeStart
)
SELECT
    RangeStart as "Start Height",
    RangeEnd as "End Height",
    COUNT(transactions.id) AS "Transaction Count",
    CASE 
        WHEN BlockCount > 0 THEN CAST(COUNT(transactions.id) AS FLOAT) / BlockCount 
        ELSE 0 
    END AS "Average Transactions Per Block" -- Calculating average transactions per block
FROM
    HeightRanges
LEFT JOIN
    transactions ON transactions.block_height >= HeightRanges.RangeStart AND transactions.block_height <= HeightRanges.RangeEnd
GROUP BY
    RangeStart, RangeEnd, BlockCount
ORDER BY
    RangeStart;
```

Some results:
```
Start Height|End Height|Transaction Count|Average Transactions Per Block|
------------+----------+-----------------+------------------------------+
         0.0|   10000.0|            10093|                        1.0093|
     10000.0|   20000.0|            10045|                        1.0045|
     20000.0|   30000.0|            10077|                        1.0077|
     30000.0|   40000.0|            10126|                        1.0126|
     40000.0|   50000.0|            10443|                        1.0443|
     50000.0|   60000.0|            15603|                        1.5603|
     60000.0|   70000.0|            23724|                        2.3724|
     70000.0|   80000.0|            25049|                        2.5049|
     80000.0|   90000.0|            24330|                         2.433|
     90000.0|  100000.0|            77097|                        7.7097|
    100000.0|  110000.0|            73093|                        7.3093|
    110000.0|  120000.0|           145882|                       14.5882|
    120000.0|  130000.0|           255586|                       25.5586|
    130000.0|  140000.0|           539712|                       53.9712|
    140000.0|  150000.0|           487765|                       48.7765|
    150000.0|  160000.0|           400154|                       40.0154|
    160000.0|  170000.0|           451247|                       45.1247|
    170000.0|  180000.0|           572250|                        57.225|
    180000.0|  190000.0|          1999277|                      199.9277|
    190000.0|  200000.0|          2175779|                      217.5779|
    200000.0|  200000.0|              388|                         388.0|
```

### Largest Transactions

```sql
SELECT 
    t.id,
    t.block_height as "Block",
    t.index_in_block as "Tx Index in Block",
    COUNT(DISTINCT i.id) AS "Input Count",
    COUNT(DISTINCT o.id) AS "Output Count",
    COUNT(DISTINCT i.id) * COUNT(DISTINCT o.id) AS "Input Count * Output Count",
    t.hash as "Tx Hash"
FROM 
    transactions t
LEFT JOIN 
    inputs i ON t.id = i.tx_id
LEFT JOIN 
    outputs o ON t.id = o.tx_id
GROUP BY 
    t.id
ORDER BY 
    "Input Count * Output Count" DESC
LIMIT 10;
```

Results:
```
Block |Tx Index in Block|Input Count|Output Count|
------+-----------------+-----------+------------+
134863|                1|        100|         999|
136273|               29|         26|        1512|
143967|                1|        135|         210|
192084|               88|        277|          73|
198445|               77|        431|          41|
198315|               52|         35|         501|
156569|                2|        104|         161|
193466|              115|        153|         101|
199328|              125|        162|          94|
195405|              147|        155|          80|
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
