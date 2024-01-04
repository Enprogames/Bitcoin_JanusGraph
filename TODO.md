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
- [x] Create `PopulateOutputProportionGraph` class to populate graph database.
- [ ] Implement tracing algorithm for graph database.
- [ ] Create some simple unit tests to validate the integrity of a few key data items in the populated database.
    - [ ] Ensuring duplicate transactions are marked as such.
    - [ ] Retrieving previous outputs from inputs.
    - [ ] Retrieving all outputs for an address.
- [ ] Visualize some interesting data.
    - [] Find some interesting transactions.

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
