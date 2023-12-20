from abc import ABC, abstractmethod
import json
import time
import traceback
from typing import Dict, Optional, Set
from pathlib import Path

import requests
import numpy as np
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.expression import func

from models.bitcoin_data import Block, Tx, Input, Output, Address, DUPLICATE_TRANSACTIONS


BLOCKCHAIN_INFO_BLOCK_ENDPOINT = "https://blockchain.info/rawblock/{height}?format=json"
BLOCKCHAIN_INFO_TX_ENDPOINT = "https://blockchain.info/rawtx/{tx_hash}?format=json"


class InvalidDataError(Exception):
    pass


class FailedRequestException(Exception):
    pass


class RateLimitException(FailedRequestException):
    pass


class UniqueIDManager:
    """Manage unique IDs for transactions, inputs, and outputs.

    In the Bitcoin blockchain, transactions, inputs, and outputs
    are not given unique IDs. This class manages the assignment
    of unique IDs to these objects. They are assigned in the order
    that they are parsed from the blockchain.

    NOTE: This class is not currently in use. It may be removed.
    """

    def __init__(self, input_npy_file='input_data.npy', output_npy_file='output_data.npy'):
        self.input_counter = 0
        self.output_counter = 0
        self.input_array = np.zeros((0, 0, 0), dtype=int)
        self.output_array = np.zeros((0, 0, 0), dtype=int)
        self.parsed_blocks = set()
        self.latest_parsed_block = -1  # Initialize to -1 to signify no blocks parsed

        if Path(input_npy_file).exists() and Path(output_npy_file).exists():
            print("Loading existing unique ID data...")
            self.load(input_npy_file, output_npy_file)
        elif Path(input_npy_file).exists() or Path(output_npy_file).exists():
            raise ValueError("Must provide both input and output npy files or neither.")

    def load_npy(self, filename):

        data = np.load(filename)
        max_id = np.max(data) if data.size > 0 else -1
        return data, max_id + 1

    def save_npy(self, data, filename):
        np.save(filename, data)

    def parse_block_json(self, block_data, block_height):

        # don't re-parse blocks and don't allow parsing out of order
        if block_height in self.parsed_blocks:
            return
        elif block_height > self.latest_parsed_block + 1:
            raise ValueError("Blocks must be parsed in order.")

        block_tx_count = len(block_data['tx'])
        current_tx_count = self.input_array.shape[1]
        new_tx_count = max(block_tx_count, current_tx_count)
        max_inputs = max(len(tx['inputs']) for tx in block_data['tx'])
        max_outputs = max(len(tx['out']) for tx in block_data['tx'])

        new_shape = (block_height + 1, new_tx_count, max(max_inputs, max_outputs))
        if self.input_array.shape != new_shape:
            np.reshape(self.input_array, new_shape)
        if self.output_array.shape != new_shape:
            np.reshape(self.output_array, new_shape)

        tx_index_in_block = 0
        for tx in block_data['tx']:
            input_index_in_tx = 0
            for _ in tx['inputs']:
                self.input_array[block_height, tx_index_in_block, input_index_in_tx] = self.input_counter
                input_index_in_tx += 1
                self.input_counter += 1

            output_index_in_block = 0
            for _ in tx['out']:
                self.output_array[block_height, tx_index_in_block, output_index_in_block] = self.output_counter
                output_index_in_block += 1
                self.output_counter += 1

            tx_index_in_block += 1

        self.parsed_blocks.add(block_height)
        self.latest_parsed_block = block_height

    def save(self, input_npy_file='input_data.npy', output_npy_file='output_data.npy'):
        self.save_npy(self.input_array, input_npy_file)
        self.save_npy(self.output_array, output_npy_file)

    def load(self, input_npy_file='input_data.npy', output_npy_file='output_data.npy'):
        self.input_array, self.input_counter = self.load_npy(input_npy_file)
        self.output_array, self.output_counter = self.load_npy(output_npy_file)

        # Initialize parsed_blocks and latest_parsed_block based on loaded data
        self.parsed_blocks = set(range(self.input_array.shape[0]))
        self.latest_parsed_block = self.input_array.shape[0] - 1 if self.input_array.shape[0] > 0 else -1

    def get_unique_input_id(self, block_height, tx_index, input_index):
        return self.input_array[block_height, tx_index, input_index]

    def get_unique_output_id(self, block_height, tx_index, output_index):
        return self.output_array[block_height, tx_index, output_index]


class BlockchainDataProviderADT(ABC):

    @abstractmethod
    def get_block(self, height: int) -> Block:
        """Get a block by its height.
        The full block with all transactions, inputs, outputs, and addresses
        should be returned, contained within the Block object.

        Args:
            height (int)

        Returns:
            Block
        """
        pass

    @abstractmethod
    def get_address(self, address: str = None, address_id: int = None) -> Address:
        """Get an address by its address string or ID.

        Args:
            address (str): The address string.

        Returns:
            Address
        """
        pass

    @abstractmethod
    def get_tx(self, tx_id: id = None, tx_hash: str = None) -> Tx:
        """Get a transaction by its ID or hash.

        Args:
            tx_id (id, optional): Defaults to None.
            tx_hash (str, optional): Defaults to None.

        Returns:
            Tx
        """
        pass

    @abstractmethod
    def get_input(self, input_id: int) -> Input:
        pass

    @abstractmethod
    def get_output(self, output_id: int) -> Output:
        """Get an output by its ID.

        Args:
            output_id (int): The ID of the output.

        Returns:
            Output
        """
        pass


class BlockchainAPIJSON:
    """Lazily make requests to the Blockchain.info API without
    persisting any data. This is slow and should only be used
    for small-scale testing.

    This is also used as the provider for the default provider
    for the PersistentBlockchainAPIData class.
    """

    def __init__(self, verbosity=1, max_retries=100, block_endpoint=BLOCKCHAIN_INFO_BLOCK_ENDPOINT,
                 tx_endpoint=BLOCKCHAIN_INFO_TX_ENDPOINT) -> None:
        """Set instance variables for the driver

        Args:
            verbosity (int, optional): How much output info to give. Defaults to 1.
            max_retries (int, optional): How many times to continue retrying API requests before stopping. Defaults to 100.
            endpoint (str, optional): Web API which returns blockchain JSON data. Defaults to 'https://blockchain.info/rawblock/'.
        """
        self.verbosity = verbosity
        self.block_endpoint = block_endpoint
        self.tx_endpoint = tx_endpoint
        self.max_retries = max_retries

    def get_block_json(self, height: int) -> dict[str, object]:
        """Using the given API endpoint, keep attempting to load a bitcoin block until the maximum number of retries have been done.

        Args:
            height (int): Height of bitcoin block to load from API.

        Raises:
            Exception: Some unknown error which may occur during population.

        Returns:
            dict[str, object]: JSON data for block data as python dictionary.
        """
        block_data: dict[str, object] = None
        successful = False
        remaining_tries = self.max_retries + 1
        while not successful and remaining_tries >= 1:
            try:
                if self.verbosity >= 3:
                    blockstore_start = time.perf_counter()
                api_response = requests.get(f'{self.block_endpoint}{str(height)}')
                block_data = api_response.json()

                # make sure the data stored is at least somewhat correct
                if 'height' not in block_data or not block_data['height'] == height:
                    raise InvalidDataError("The block data received was invalid.")
                successful = True
                if self.verbosity >= 3:
                    print(f"block {height} successfully loaded in {time.perf_counter() - blockstore_start} seconds")

            except (json.decoder.JSONDecodeError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                    InvalidDataError) as e:
                print(traceback.format_exc())
                remaining_tries -= 1
                if remaining_tries >= 1:
                    print(f'{e} for block {height}. Retrying in 5 seconds.')
                    time.sleep(5)
                else:
                    block_data = None
            except Exception as e:
                traceback.print_exc()
                remaining_tries = 0
                print(f"Got unhandled {type(e)}")
                raise e

        if not block_data:
            raise FailedRequestException(f"After trying {self.max_retries+1} time(s),"
                                         f" the block data was not successfully retrieved from {self.block_endpoint}.")

        return block_data

    def get_blocks_json(self, heights: list[int]) -> dict[int, dict[str, object]]:
        return {height: self.get_block(height) for height in heights}

    def get_tx_json(self, _hash: str) -> dict[str, object]:
        """Using the given API endpoint, keep attempting to load a bitcoin transaction until the maximum number of retries have been done.

        Args:
            _hash (str): Hash of bitcoin transaction to load from API.

        Raises:
            Exception: Some unknown error which may occur during population.

        Returns:
            dict[str, object]: JSON data for transaction data as python dictionary.
        """
        tx_data: dict[str, object] = None
        successful = False
        remaining_retries = self.max_retries
        while not successful and remaining_retries >= 1:
            try:
                if self.verbosity >= 3:
                    txstore_start = time.perf_counter()

                api_response = requests.get(f'{self.tx_endpoint}{str(_hash)}')
                if api_response.status_code == 429:
                    raise RateLimitException("Rate limit response given from API")
                if not api_response.ok:
                    raise FailedRequestException("Error response from API")
                tx_data = api_response.json()

                # expand the list and store
                if 'hash' not in tx_data or tx_data['hash'] != _hash:
                    raise InvalidDataError("The transaction had either no hash or the wrong one")
                successful = True
                if self.verbosity >= 3:
                    print(f"tx {_hash} successfully loaded in {time.perf_counter() - txstore_start} seconds")

            except (json.decoder.JSONDecodeError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                    AssertionError,
                    ) as e:
                print(traceback.format_exc())
                print(f'{e} for tx {_hash}. Retrying in 5 seconds.')
                time.sleep(5)
                remaining_retries -= 1
            except Exception as e:
                traceback.print_exc()
                remaining_retries = 0
                raise e

        return tx_data


class PersistentBlockchainAPIData(BlockchainDataProviderADT):
    """Persist data from the Blockchain.info API to a database.

    Args:
        BlockchainDataProviderADT (ABC): Implements the abstract
        interface for Bitcoin data providers.
    """

    def __init__(self,
                 data_provider: BlockchainAPIJSON = None):
        self.data_provider = data_provider
        self.current_tx_id = 0
        self.current_input_id = 0
        self.current_output_id = 0
        self.current_address_id = 0
        # self.unique_id_manager = unique_id_manager if unique_id_manager else UniqueIDManager()

        self.duplicate_transactions = {}
        for dup_tx in DUPLICATE_TRANSACTIONS:
            height = dup_tx['block_height']
            tx_hash = dup_tx['tx_hash']
            self.duplicate_transactions[height] = tx_hash

    def get_block(self, session: Session, height: int) -> Block:
        block = session.query(Block) \
            .options(
                joinedload(Block.transactions)
                .joinedload(Tx.inputs)
                .joinedload(Input.prev_out),
                joinedload(Block.transactions)
                .joinedload(Tx.outputs)
                .joinedload(Output.address)
        ) \
            .filter_by(height=height).first()

        if block:
            return block
        # If block not found in the database, raise error
        raise FileNotFoundError(f"Block with height {height} not found in database")

    def get_tx(self, session: Session, tx_id: int = None, tx_hash: str = None) -> Tx:
        options = (
            joinedload(Tx.inputs)
            .joinedload(Input.prev_out),
            joinedload(Tx.outputs)
            .joinedload(Output.address)
        )

        if not (tx_id is not None or tx_hash is not None):
            raise ValueError("Must provide either tx_id or tx_hash")
        if tx_id:
            tx_obj = session.query(Tx).options(
                options
            ).filter_by(id=tx_id).first()

            if not tx_obj:
                raise FileNotFoundError(f"Transaction with ID {tx_id} not found in database")
        else:
            tx_obj = session.query(Tx).options(
                options
            ).filter_by(hash=tx_hash).first()

            if not tx_obj:
                raise FileNotFoundError(f"Transaction with hash {tx_hash} not found in database")

        return tx_obj

    def get_input(self, session: Session, input_id: int) -> Input:
        input_obj = session.query(Input).options(
            joinedload(Input.prev_out)
        ).filter_by(id=input_id).first()

        if input_obj:
            return input_obj
        raise FileNotFoundError(f"Input with ID {input_id} not found in database")

    def get_output(self, session: Session, output_id: int) -> Output:
        output_obj = session.query(Output).options(
            joinedload(Output.address)
        ).filter_by(id=output_id).first()

        if output_obj:
            return output_obj
        raise FileNotFoundError(f"Output with ID {output_id} not found in database")

    def get_address(self, session: Session, address: str = None, address_id: int = None) -> Address:
        if not (address or address_id):
            raise ValueError("Must provide either address or address_id")
        if address:
            address_obj = session.query(Address).filter_by(addr=address).first()

            if not address_obj:
                raise FileNotFoundError(f"Address with address {address} not found in database")
        else:
            address_obj = session.query(Address).filter_by(id=address_id).first()

            if not address_obj:
                raise FileNotFoundError(f"Address with ID {address_id} not found in database")

        return address_obj

    def __populate_addresses(self, session: Session, block: Block):

        addr_dict = {}
        outputs = []

        with session.no_autoflush:
            for tx in block.transactions:
                for output in tx.outputs:
                    addr = output.address_addr
                    if addr is not None and addr not in addr_dict:
                        # see if the address already exists
                        address = session.query(Address).filter_by(addr=addr).first()

                        # if the address doesn't exist, create it
                        if not address:
                            address = Address()
                            address.addr = addr
                            address.id = self.current_address_id
                            self.current_address_id += 1
                            address.outputs = []
                        addr_dict[addr] = address

                    if addr is not None:
                        addr_dict[addr].outputs.append(output)
                        output.address = addr_dict[addr]
                        outputs.append(output)

            session.add_all(list(addr_dict.values()) + outputs)

    def parse_tx(self, session: Session, tx_index_in_block: int, json_data: dict,
                 block: Block, block_tx_index_dict: Dict[int, int]) -> Tx:

        tx = Tx()
        block.transactions.append(tx)
        tx.id = self.current_tx_id
        self.current_tx_id += 1

        tx.hash = json_data['hash']
        tx.block = block
        tx.block_height = json_data['block_height']
        tx.is_duplicate = (tx.block_height in self.duplicate_transactions
                           and self.duplicate_transactions[tx.block_height] == tx.hash)
        tx.index_in_block = tx_index_in_block
        tx.index = json_data['tx_index']

        assert 'inputs' in json_data, f"Inputs not found in transaction {tx.hash}"
        assert 'out' in json_data, f"Outputs not found in transaction {tx.hash}"

        tx.inputs = []
        for input_idx, input_data in enumerate(json_data['inputs']):
            # see if this is a coinbase input. if it is, don't populate it
            # the first tx is always a coinbase tx
            if tx_index_in_block == 0:
                continue
            new_input = Input()
            new_input.id = self.current_input_id
            self.current_input_id += 1

            new_input.tx_index = int(tx.index)
            new_input.index_in_tx = int(input_idx)

            prev_out_tx_index = int(input_data['prev_out']['tx_index'])
            prev_out_index_in_tx = int(input_data['prev_out']['n'])
            if prev_out_tx_index in block_tx_index_dict:
                # the previous output is in a transaction in the same block
                prev_out_tx_index_in_block = block_tx_index_dict[prev_out_tx_index]
                assert prev_out_index_in_tx <= len(block.transactions[prev_out_tx_index_in_block].outputs) - 1, \
                    f"Previous output for non-coinbase input {new_input.id} not found in block" \
                    f" (prev_out_tx_index_in_block={prev_out_tx_index_in_block}, tx_index={prev_out_tx_index}," \
                    f" index_in_tx={prev_out_index_in_tx}), tx_hash={tx.hash}, block_height={tx.block_height}," \
                    f" tx_index_in_block={tx_index_in_block})"

                prev_output = block.transactions[prev_out_tx_index_in_block].outputs[prev_out_index_in_tx]
            else:
                # get previous output that should have already been populated
                prev_output = session.query(Output).filter(
                    Output.transaction.has(index=int(prev_out_tx_index)),
                    Output.index_in_tx == int(prev_out_index_in_tx)
                ).first()

            assert prev_output is not None, \
                f"Previous output for non-coinbase input {new_input.id} not found in database" \
                f" (tx_index={prev_out_tx_index}, index_in_tx={prev_out_index_in_tx})" \
                f" (tx_hash={tx.hash}, block_height={tx.block_height}, tx_index_in_block={tx_index_in_block})"

            new_input.prev_out = prev_output
            tx.inputs.append(new_input)

        tx.outputs = []
        for output_idx, output_data in enumerate(json_data['out']):
            new_output = Output()

            new_output.id = self.current_output_id
            self.current_output_id += 1

            new_output.index_in_tx = int(output_idx)
            new_output.value = int(output_data['value'])
            new_output.tx_index = int(tx.index)
            if 'addr' in output_data:
                new_output.address_addr = str(output_data['addr'])
            else:
                new_output.valid = False
                new_output.address_addr = None
            tx.outputs.append(new_output)

        return tx

    def parse_block(self, session: Session, height: int = None, json_data: dict = None) -> Block:
        if not (height or json_data):
            raise ValueError("Must provide either height or json_data")
        if not json_data:
            json_data = self.data_provider.get_block_json(height=height)

        block = Block()
        block.height = json_data['height']
        block_tx_index_dict = {tx['tx_index']: i for i, tx in enumerate(json_data['tx'])}
        block.transactions = []
        for tx_idx, tx_json in enumerate(json_data['tx']):
            self.parse_tx(session, tx_index_in_block=tx_idx, json_data=tx_json,
                          block=block, block_tx_index_dict=block_tx_index_dict)

        return block

    def repopulate_addresses(self, session: Session,
                             block_heights: list[int] = None,
                             show_progressbar=False):

        if block_heights is None:
            block_heights = session.query(Block.height).distinct()
            block_heights = [height for (height,) in block_heights]
        else:
            block_heights = list(block_heights)
            block_heights.sort()

        # highest_block = block_heights[-1]

        if show_progressbar:
            from tqdm import tqdm
            block_heights = tqdm(block_heights)

        for block_height in block_heights:
            self.__populate_addresses(session, block_height)  # , commit=False)
            # if (block_height > 0 and block_height % 100 == 0) or block_height == highest_block:
            #     session.commit()

    def populate_block(self, session: Session, block_height: int, populate_addresses=True):
        # parse the block into the unique_id_manager
        block_json = self.data_provider.get_block_json(height=block_height)

        ### find the current highest input ID, output ID, and TX ID to continue from

        highest_tx = session.query(func.max(Tx.id)).scalar()
        self.current_tx_id = int(highest_tx) + 1 if highest_tx is not None else 0

        highest_input = session.query(func.max(Input.id)).scalar()
        self.current_input_id = int(highest_input) + 1 if highest_input is not None else 0

        highest_output = session.query(func.max(Output.id)).scalar()
        self.current_output_id = int(highest_output) + 1 if highest_output is not None else 0

        highest_address = session.query(func.max(Address.id)).scalar()
        self.current_address_id = int(highest_address) + 1 if highest_address is not None else 0

        assert block_height == 0 or (
            highest_tx is not None and highest_output is not None
            and self.current_tx_id >= 0 and self.current_output_id >= 0)

        # self.unique_id_manager.parse_block_json(block_json, block_height)
        # self.unique_id_manager.save()
        # Populate block data using data provider
        block = self.parse_block(session, height=block_height, json_data=block_json)

        if populate_addresses:
            self.__populate_addresses(session, block)

        # Save block to database
        session.add(block)
        session.commit()

    def populate_blocks(self,
                        session: Session,
                        block_heights: list[int],
                        show_progressbar=False,
                        fail_if_exists=False):
        block_heights = list(block_heights)
        block_heights.sort()

        # get the highest block height that already exists in the database
        highest_block = session.query(Block).order_by(Block.height.desc()).first()
        if fail_if_exists and highest_block is not None:
            raise ValueError(f"Blocks already exist in database. Highest block height: {highest_block.height}")

        # assume blocks are populated in order and start from the first unpopulated block
        if highest_block is not None:
            if highest_block.height > block_heights[-1]:
                block_heights = []
            else:
                block_heights = block_heights[block_heights.index(highest_block.height) + 1:]

        if show_progressbar:
            from tqdm import tqdm
            block_heights = tqdm(block_heights)

        for block in block_heights:
            self.populate_block(session, block)
