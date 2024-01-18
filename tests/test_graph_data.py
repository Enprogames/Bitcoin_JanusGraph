import pytest
from sqlalchemy import distinct, exists, or_
from sqlalchemy.orm import Session
from models.bitcoin_data import Address, Tx, Output, Input, Block, ManualProportion
from models.base import Base, SessionLocal
from blockchain_data_provider import PersistentBlockchainAPIData

from graph_populate import PopulateOutputProportionGraph


@pytest.mark.skip("TODO: test that the graph is populated correctly")
def test_custom_proportions():
    """Some custom input/output proportions are expected to be present in the database.
    The graph database will be populated with these. We will test that are set correctly.
    Then, they will be reset back to the original haircut-method values, and we will
    ensure that these are correct too.
    """
    blockchain_data_provider = PersistentBlockchainAPIData()
    populator = PopulateOutputProportionGraph(blockchain_data_provider)

    with SessionLocal() as session:
        # populate manual proportion values
        affected_txs = ManualProportion.get_affected_txs(session)
        populator.apply_manual_edge_proportions(session)

    # TODO: test that the proportions are correct

    with SessionLocal() as session:
        # reset manual proportion values
        populator.reset_manual_edge_proportions(session)

    # TODO: test that all proportions are reset to the original haircut method values
