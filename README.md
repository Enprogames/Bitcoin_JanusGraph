# Bitcoin Data Graph

# Usage
This project utilizes Docker and Docker Compose to manage its environment. The provided Makefile simplifies the process of building, running, and managing the application.

## Prerequisites

Before you begin, ensure you have installed:

- Docker
- Docker Compose

## Getting Started

To get started with the project, first clone the repository and navigate into the project directory.

## Using the Makefile

The Makefile includes several commands to manage the Docker containers, networks, and volumes associated with the project.

### Building the Project

To build the Docker images for the project:

```bash
make build
```

### Running the Application

To start the application in Docker containers:

```bash
make run
```

### Populating Data

The project supports populating data into the database. You can populate blocks and graph data using the following commands:

- To populate blocks up to a default height:

```bash
make populate_blocks
```

- To populate blocks up to a specific height (e.g., height 200):

```bash
make populate_blocks BLOCK_HEIGHT=200
```

- To populate the graph with data from the blockchain database:

```bash
make populate_graph
```

### Running Tests

To run tests in the application:

```bash
make test
```

### Stopping the Application

To stop the running Docker containers:

```bash
make stop
```

### Cleaning Up

To remove Docker containers and networks created by `make run`:

```bash
make clean
```

For a full cleanup, including removal of volumes, images, and orphan containers:

```bash
make full_clean
```

## Additional Commands

- To view the status of the containers:

```bash
make ps
```

- To start stopped containers:

```bash
make start
```

- To restart the containers:

```bash
make restart
```

## Conclusion

The Makefile is designed to simplify Docker container management in the development process. For any additional commands or modifications, refer to the Makefile in the project repository.

# Description

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
