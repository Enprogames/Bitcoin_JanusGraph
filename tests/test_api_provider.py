import pytest
import numpy as np

from blockchain_data_provider import UniqueIDManager


TEST_INPUT_FILE = 'test_input.npy'
TEST_OUTPUT_FILE = 'test_output.npy'


@pytest.fixture(autouse=True)
def setup():
    # code that runs before the tests
    import os
    if os.path.exists(TEST_INPUT_FILE):
        os.remove(TEST_INPUT_FILE)
    if os.path.exists(TEST_OUTPUT_FILE):
        os.remove(TEST_OUTPUT_FILE)
    yield
    # code that runs after the tests
    if os.path.exists(TEST_INPUT_FILE):
        os.remove(TEST_INPUT_FILE)
    if os.path.exists(TEST_OUTPUT_FILE):
        os.remove(TEST_OUTPUT_FILE)


def test_init():
    manager = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    assert manager.input_counter == 0
    assert manager.output_counter == 0
    assert np.array_equal(manager.input_array, np.zeros((0, 0, 0), dtype=int))
    assert np.array_equal(manager.output_array, np.zeros((0, 0, 0), dtype=int))


def test_parse_block():
    manager = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    assert list(manager.parsed_blocks) == []
    block_data = {
        'hash': 'dummy_hash',
        'tx': [
            {
                'hash': 'dummy_tx_hash_1',
                'inputs': [{}],
                'out': [{}, {}],
            },
            {
                'hash': 'dummy_tx_hash_2',
                'inputs': [{}],
                'out': [{}],
            }
        ]
    }

    with pytest.raises(ValueError):
        manager.parse_block_json(block_data, block_height=5)

    manager.parse_block_json(block_data, block_height=0)

    assert manager.input_counter == 2
    assert manager.output_counter == 3
    assert manager.input_array.shape == (1, 2, 2)
    assert manager.output_array.shape == (1, 2, 2)
    assert list(manager.parsed_blocks) == [0]

    manager.parse_block_json(block_data, 1)

    # all of the same data again
    assert manager.input_counter == 4
    assert manager.output_counter == 6
    assert manager.input_array.shape == (2, 2, 2)
    assert manager.output_array.shape == (2, 2, 2)
    assert manager.input_array[0, 0, 0] == 0
    assert list(manager.parsed_blocks) == [0, 1]

    # ensure we can parse the same block twice
    manager.parse_block_json(block_data, 0)


def test_save_and_load():
    manager1 = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    block_data = {
        'hash': 'dummy_hash',
        'tx': [
            {
                'hash': 'dummy_tx_hash_1',
                'inputs': [{}],
                'out': [{}, {}],
            }
        ]
    }
    manager1.parse_block_json(block_data, block_height=0)
    manager1.save('test_input.npy', 'test_output.npy')

    manager2 = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    manager2.load('test_input.npy', 'test_output.npy')

    assert np.array_equal(manager1.input_array, manager2.input_array)
    assert np.array_equal(manager1.output_array, manager2.output_array)


def test_get_unique_id():
    manager = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    block_data = {
        'hash': 'dummy_hash',
        'tx': [
            {
                'hash': 'dummy_tx_hash_1',
                'inputs': [{}],
                'out': [{}, {}],
            },
            {
                'hash': 'dummy_tx_hash_2',
                'inputs': [{}],
                'out': [{}],
            }
        ]
    }

    manager.parse_block_json(block_data, block_height=0)

    assert manager.get_unique_input_id(0, 0, 0) == 0
    assert manager.get_unique_input_id(0, 1, 0) == 1
    assert manager.get_unique_output_id(0, 0, 0) == 0
    assert manager.get_unique_output_id(0, 0, 1) == 1
    assert manager.get_unique_output_id(0, 1, 0) == 2


def test_load_nonempty_file():
    
    # create a new manager with an empty file and populate it
    manager1 = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    block_data = {
        'hash': 'dummy_hash',
        'tx': [
            {
                'hash': 'dummy_tx_hash_1',
                'inputs': [{}],
                'out': [{}, {}],
            }
        ]
    }
    manager1.parse_block_json(block_data, block_height=0)
    manager1.save('test_input.npy', 'test_output.npy')

    # create a new manager with the same file and load it
    manager2 = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    manager2.load('test_input.npy', 'test_output.npy')

    # ensure the two managers are the same
    assert np.array_equal(manager1.input_array, manager2.input_array)

    # ensure that if we parse the same block again, the managers are still the same
    manager1.parse_block_json(block_data, block_height=0)
    assert np.array_equal(manager1.input_array, manager2.input_array)

    # if we parse a new block, they should be different
    manager1.parse_block_json(block_data, block_height=1)
    assert not np.array_equal(manager1.input_array, manager2.input_array)


def test_shape_integrity():
    # ensure that if the shape changes, the manager will successfully
    # handle it
    
    # First, ensure that if a block with more transactions is parsed,
    # the shape of the arrays will increase
    manager = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    small_block_data = {
        'hash': 'dummy_hash',
        'tx': [
            {
                'hash': 'dummy_tx_hash_1',
                'inputs': [{}],
                'out': [{}, {}],
            }
        ]
    }
    manager.parse_block_json(small_block_data, block_height=0)
    assert manager.input_array.shape == (1, 1, 2)
    large_block_data = {
        'hash': 'dummy_hash',
        'tx': [
            {
                'hash': 'dummy_tx_hash_1',
                'inputs': [{}],
                'out': [{}, {}],
            },
            {
                'hash': 'dummy_tx_hash_2',
                'inputs': [{}],
                'out': [{}],
            }
        ]
    }
    
    manager.parse_block_json(large_block_data, block_height=1)
    assert manager.input_array.shape == (2, 2, 2)

    # reset
    import os
    if os.path.exists(TEST_INPUT_FILE):
        os.remove(TEST_INPUT_FILE)
    if os.path.exists(TEST_OUTPUT_FILE):
        os.remove(TEST_OUTPUT_FILE)
    
    # second, ensure that if a block with more transactions is parsed,
    # followed by a block with fewer transactions, the shape of the
    # arrays will not change
    manager = UniqueIDManager(TEST_INPUT_FILE, TEST_OUTPUT_FILE)
    manager.parse_block_json(large_block_data, block_height=0)
    assert manager.input_array.shape == (1, 2, 2)
    manager.parse_block_json(small_block_data, block_height=1)
    assert manager.input_array.shape == (2, 2, 2)


# @pytest.mark.skip("This test is slow")
# def test_get_block():

#     provider = SlowBlockchainAPIData()

#     block170 = provider.get_block(170)
#     assert block170.height == 170
