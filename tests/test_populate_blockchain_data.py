import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils import MockDataProvider
from models.bitcoin_data import Base, Block, Tx
from blockchain_data_provider import PersistentBlockchainAPIData

# Constants
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def session():
    # Set up an in-memory SQLite database for testing
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def blockchain_api():
    # Create an instance of your PersistentBlockchainAPIData
    api = PersistentBlockchainAPIData(data_provider=MockDataProvider())
    return api


def test_get_block(session, blockchain_api):
    # Test getting a block from the database
    test_height = 0  # Example block height
    blockchain_api.populate_block(session, test_height)
    block = blockchain_api.get_block(session, test_height)
    assert block is not None
    assert block.height == test_height
