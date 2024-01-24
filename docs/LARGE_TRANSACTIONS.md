# Large Transactions
As part of my research, I am investigating very large transactions which consist of several inputs and outputs. I suspect that these might be involved in Bitcoin "laundry" transactions, or simply in exchange transactions where many user's coins are sent as a batch.

Before diving into that, it is also interesting to count the number of transactions that have a more regular number of inputs and outputs. Most commonly, someone will combine several inputs, then send to two outputs: one for the recipient, and one for change since it is very rare that the inputs will exactly match the desired output amount. The following query finds the number of transactions with exactly two outputs:

```sql
-- Number of non-coinbase transactions with exactly two outputs
select 'non_coinbase_two_op_count' as category, count(*) as "count"
from (
	select distinct tx.id
	from transactions as tx
	join outputs op on tx.id=op.tx_id
	where tx.index_in_block > 0
	group by tx.id
	having count(op.id) = 2
) AS subquery1
union all
-- Number of non-coinbase transactions
select 'non_coinbase_count' as category, count(*) as "count"
from (
	select distinct tx.id
	from transactions as tx
	join outputs op on tx.id=op.tx_id
	where tx.index_in_block > 0
	group by tx.id
) AS subquery2;
```

The results are as follows:
```
category                 |count  |
-------------------------+-------+
non_coinbase_two_op_count|6489730|
non_coinbase_count       |7116695|
```

This means that 91% of non-coinbase transactions have exactly two outputs. This is a very strong indicator that the transaction is a normal user transaction. So in this early set of transactions for the first 200,000 blocks, there are 626,965 that do not conform to this pattern.

The following query finds large transactions by multiplying the number of inputs and outputs. This is a very naive approach, but it is a good starting point.

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

The results are as follows:
```
id     |Block |Tx Index in Block|Input Count|Output Count|Input Count * Output Count|Tx Hash                                                         |
-------+------+-----------------+-----------+------------+--------------------------+----------------------------------------------------------------+
 951352|134863|                1|        100|         999|                     99900|1c19389b0461f0901d8eace260764691926a5636c74bd8a3cc68db08dbbeb80a|
1035342|136273|               29|         26|        1512|                     39312|d50871077b83f7f2497a65c8ff00172c9bbfefd46cd2c4c258a2cccbad337d82|
1441873|143967|                1|        135|         210|                     28350|67e10ee7cb45ad344cd714500b61d1dac08886619e668ad0ba37d7c535cade2b|
5575007|192084|               88|        277|          73|                     20221|41cb9d99f55d7ba7a42afd8abba20a9313eaca4558bb66319cc4e35b18418174|
7020591|198445|               77|        431|          41|                     17671|2f66913adbe3d6e638a2f8bf93d5fdcf04b121c2fadd34da6511095e476db15d|
6987093|198315|               52|         35|         501|                     17535|06bc7098ceef9e2642c56972f8ef6b5822894760042a770f33d2fbb5eec13d68|
1992599|156569|                2|        104|         161|                     16744|9e33084a8713e0872f9d509a19adebe47e6c66da8154533aadf1e4a58272dea0|
5855968|193466|              115|        153|         101|                     15453|b590c2046f380e504b2407fcd9501d9ed07d95243b6797dc1a5c770fa432df8a|
7186522|199328|              125|        162|          94|                     15228|e43d25989cabf46892be363260605c51107f396257ce51d2db17302d17ad1bf6|
6336328|195405|              147|        155|          80|                     12400|916e4eb36b8d2618163422cc705163f56e3944922e7c5e056b0bc9d3fb8be057|
```

Transaction `1c19389b0461f0901d8eace260764691926a5636c74bd8a3cc68db08dbbeb80a` is the largest transaction by this metric. It has 100 inputs and 999 outputs. I want to do research to see if this is either a "laundry" transaction or one used by an exchange, or simply strange user activity.
