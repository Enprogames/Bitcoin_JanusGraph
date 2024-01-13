import pytest
from sqlalchemy import distinct, exists, or_
from sqlalchemy.orm import Session
from models.bitcoin_data import Address, Tx, Output, Input, Block
from models.base import Base, SessionLocal
from blockchain_data_provider import PersistentBlockchainAPIData


MAX_HEIGHT = 10_000


@pytest.fixture(scope="function")
def session():
    # use the real database for testing
    # this is fine because we are only reading from it
    session: Session = SessionLocal()
    yield session
    session.close()


def test_address_unique_ids(session: Session):
    # ensure ids count up from 0. query and order by block height, index in block, and index in tx
    # Subquery to order addresses based on block height, index in block, and index in tx
    subquery = session.query(Address.id.label("address_id")) \
        .join(Output, Address.outputs) \
        .join(Tx, Output.transaction) \
        .filter(Tx.block_height <= MAX_HEIGHT) \
        .order_by(Tx.block_height, Tx.index_in_block, Output.index_in_tx) \
        .subquery()

    # Query to select distinct address IDs from the ordered subquery
    address_ids = session.query(subquery.c.address_id)\
        .group_by(subquery.c.address_id)\
        .all()
    address_ids = [address_id for address_id, in address_ids]
    assert len(set(address_ids)) == len(address_ids)
    assert address_ids == list(range(len(address_ids)))


def test_output_unique_ids(session: Session):
    # same for outputs
    output_ids = session.query(Output.id) \
        .join(Tx, Output.transaction) \
        .filter(Tx.block_height <= MAX_HEIGHT) \
        .order_by(Tx.block_height, Tx.index_in_block, Output.index_in_tx).all()
    output_ids = [output_id for output_id, in output_ids]
    assert len(set(output_ids)) == len(output_ids)
    assert output_ids == list(range(len(output_ids)))


def test_input_unique_ids(session: Session):
    # same for inputs
    input_ids = session.query(Input.id)\
                       .join(Tx, Input.transaction)\
                       .filter(Tx.block_height <= MAX_HEIGHT)\
                       .order_by(Tx.block_height, Tx.index_in_block, Input.index_in_tx).all()
    input_ids = [input_id for input_id, in input_ids]
    assert len(set(input_ids)) == len(input_ids)
    assert input_ids == list(range(len(input_ids)))


def test_txs_unique_ids(session: Session):
    # same for transactions
    tx_ids = session.query(Tx.id)\
                    .filter(Tx.block_height <= MAX_HEIGHT)\
                    .order_by(Tx.block_height, Tx.index_in_block).all()
    tx_ids = [tx_id for tx_id, in tx_ids]
    assert len(set(tx_ids)) == len(tx_ids)
    assert tx_ids == list(range(len(tx_ids)))


def test_tx_order_of_appearance(session: Session):

    transactions = session.query(Tx.id)\
                          .filter(Tx.block_height <= MAX_HEIGHT)\
                          .order_by(Tx.block_height, Tx.index_in_block)\
                          .all()
    assert all([tx_id == i for i, (tx_id,) in enumerate(transactions)])


def test_address_order_of_appearance(session: Session):

    # Query all addresses joined with their first occurrence in a transaction
    subquery = session.query(Address.id.label("address_id"))\
        .join(Output, Address.outputs)\
        .join(Tx, Output.transaction)\
        .filter(Tx.block_height <= MAX_HEIGHT)\
        .order_by(Tx.block_height, Tx.index_in_block, Output.index_in_tx)\
        .subquery()

    first_occurrences = session.query(subquery.c.address_id)\
        .group_by(subquery.c.address_id)\
        .all()

    # Extract address IDs and ensure they are in the correct order
    address_ids = [address_id for (address_id,) in first_occurrences]

    assert address_ids == sorted(address_ids), "Address IDs are not in the order of appearance"


def test_get_txs_for_blocks(session: Session):
    tx: Tx
    data_provider = PersistentBlockchainAPIData()

    for tx in data_provider.get_txs_for_blocks(
        session,
        min_height=0,
        max_height=MAX_HEIGHT,
        buffer=2000
    ):

        tx_sum = tx.total_input_value()
        output: Output
        for output in tx.outputs:
            if not output.valid:
                continue

            assert output.value is not None
            # ensure each input's previous output exists
        assert (
            session.query(Input)
                   .outerjoin(Output, Input.prev_out_id == Output.id)
                   .filter(Input.tx_id == tx.id,
                           or_(Input.prev_out_id.is_(None), Output.id.is_(None)))
                   .first()
        ) is None
