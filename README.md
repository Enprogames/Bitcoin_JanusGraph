# Bitcoin Data Graph
The main point of this project is to effectively demonstrate Bitcoin tracing in a graph database, and to develop algorithms to achieve it.

## Main Challenges in Tracing
The main challanges when attempting to trace Bitcoin transaction histories are:
- The massive scale of the Bitcoin blockchain dataset and the transactions therein,
- The complexity of the Bitcoin transaction data model, and
- the presence of "bad data", such as duplicate transactions.

## Complexity of the Bitcoin Data Model
To go into more detail about the complexity of the Bitcoin transaction data model, we need only examine some real transactions. There exist transactions where individuals send coin directly to themselves, ones where they send coin back and forth between themselves and other addresses multiple times, and ones where hundreds of addresses send coin to hundreds of other addresses in the same transaction.

Because of the way the Bitcoin core protocol works, all of the addresses used to send coin in one transaction are presumably owned and controlled by one individual or entity.

### Duplicate Transactions
There are two occurrences of duplicate transactions on the Bitcoin Blockchain. On block 91,842, a transaction exists that has the same hash as a previous one. And on 91,880, a similar case occurred. This issue was fixed in BIP-30, so the issue will no longer occur. But despite this, we must still handle this corner case.

When a transaction is duplicated, the nature of the Bitcoin core software ensues that only the newest transaction is spendable. For this reason, it makes sense that the graph representations of Bitcoin transaction data only consider the newest one.

# Graph Representations

## Address Proportion Graph
In this graph representation, each node is an address, and each edge is a haircut proportion between two output nodes. Two addresses will be connected based on the addresses present in these output nodes. The sender will have an edge directed at the recipient.

Tracing this graph ... TODO: 

## Output Proportion Graph
In this graph representation, each node is an output, and each edge is a haircut proportion between two output nodes.

Tracing this graph is straightforward, simply involving a backtracking depth-first traversal from a given node backwards to all of its senders. Since the graph only goes forwards, and thus contains no cycles, we only need to concern ourselves with looking backwards.
