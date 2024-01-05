from collections.abc import Iterator, Generator
from abc import ABC, abstractmethod
import json
import time
import copy
import traceback
from typing import Dict
from pathlib import Path

import requests
import traceback
import concurrent.futures
import asyncio
import aiohttp
import requests
import numpy as np
from sqlalchemy import tuple_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.expression import func

from aio_utils import asyncio_run, asyncio_gather
from models.bitcoin_data import Block, Tx, Input, Output, Address, DUPLICATE_TRANSACTIONS


BLOCKCHAIN_INFO_BLOCK_ENDPOINT = "https://blockchain.info/rawblock/"
BLOCKCHAIN_INFO_TX_ENDPOINT = "https://blockchain.info/rawtx/"


def chunked_ranges(lowest, highest, buffer: int = 100) -> list[tuple[int, int]]:

    ranges = []

    total = highest - lowest + 1
    if buffer > total:
        buffer = total

    start = lowest
    if buffer > 0:
        while start <= highest - buffer + 1:
            ranges.append((start, start + buffer - 1))
            start += buffer

        remaining_blocks = highest - start + 1
        if remaining_blocks > 0:
            ranges.append((highest - remaining_blocks +
                          1 * (start > lowest), highest))
    else:
        ranges.append((0, 0))

    return ranges


def chunked_indices(items: list, buffer: int):
    return [(start, end + 1) for (start, end) in chunked_ranges(0, len(items) - 1, buffer)]


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

                self.block_endpoint = self.block_endpoint.strip('/')
                api_response = requests.get(f'{self.block_endpoint}/{str(height)}')
                block_data = api_response.json()

                # make sure the data stored is at least somewhat correct
                if 'height' not in block_data or not block_data['height'] == height:
                    error_message = f"contains attributes {list(block_data.keys())}"
                    if 'error' in block_data and 'message' in block_data:
                        error_message = f"Got error {block_data['error']} with message {block_data['message']}"
                    raise InvalidDataError(f"The block data received was invalid. Error info from api: {error_message}.")
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
        return {height: self.get_block_json(height) for height in heights}

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


class BlockchainAPIAsync:
    def __init__(self, block_endpoint='https://blockchain.info/rawblock/', max_retries=20, max_connections=20,
                 disable_http_keep_alive=True, timeout=50, retry_delay: float = 10,
                 verbosity: int = 1):

        self.block_json: dict[int, dict[str, object]] = {}
        self.block_endpoint = block_endpoint

        self.request_heights = {}
        self.failed_heights = set()

        # retrying if a request fails
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Settings for HTTP session
        self.timeout = timeout
        self.max_connections = max_connections
        self.disable_http_keep_alive = disable_http_keep_alive

        self.errors = []
        self.verbosity = verbosity

    async def __get_block_async(self, session: aiohttp.ClientSession, height: int) -> asyncio.Task:
        api_request = f'{self.block_endpoint}{height}'
        self.request_heights[api_request] = height

        try:
            retrieval_task = await session.get(api_request, timeout=self.timeout)
            return retrieval_task
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError,
                aiohttp.client_exceptions.ClientConnectionError) as e:
            if self.verbosity >= 3:
                print(f"{type(e).__name__} occurred while getting block at height {height}")
            if not self.errors or (self.errors and self.errors[-1] != type(e)):
                self.errors.append(type(e))
                if self.verbosity >= 2:
                    print(f"Got {type(e).__name__}: {e}")
            self.failed_heights.add(height)
        except Exception as e:
            if self.verbosity >= 3:
                print(f"Unhandled {type(e).__name__} occurred while getting block at height {height}")
            if not self.errors or (self.errors and self.errors[-1] != type(e)):
                self.errors.append(type(e))
                if self.verbosity >= 2:
                    print(f"Got unhandled {type(e).__name__}: {e}")
            raise e

        return None

    async def __get_blocks_async(self, heights: list[int]):

        tcp_connector = aiohttp.TCPConnector(limit=self.max_connections,
                                             force_close=self.disable_http_keep_alive)
        async with aiohttp.ClientSession(connector=tcp_connector) as session:
            tasks: list[asyncio.Task] = []
            for height in heights:
                tasks.append(self.__get_block_async(session, height))
            responses: asyncio.Future[list[aiohttp.ClientResponse]] = await asyncio_gather(*tasks, return_exceptions=True)

            response: aiohttp.ClientResponse
            for response in responses:
                if response:
                    try:
                        if isinstance(response, Exception):
                            raise response
                        block_height = self.request_heights[str(response.url)]
                        if response.status == 429:
                            raise RateLimitException(f"Got rate limited for too many requests at block {block_height}.")
                        if not response.ok:
                            raise FailedRequestException(f"The request for block {block_height}"
                                                         f" failed with code {response.status}.")
                        block_json: dict[str, object] = await response.json()
                        if not ('height' in block_json and block_height == block_json['height']):
                            raise InvalidDataError(f"The JSON data returned for block {block_height} came back invalid.")
                        self.block_json[block_height] = block_json
                    except (AssertionError, json.decoder.JSONDecodeError, FailedRequestException,
                            asyncio.TimeoutError, aiohttp.client_exceptions.ServerDisconnectedError,
                            InvalidDataError, aiohttp.client_exceptions.ClientPayloadError) as e:
                        failed_height = self.request_heights[str(response.url)]
                        self.failed_heights.add(failed_height)
                        if not self.errors or (self.errors and self.errors[-1] != type(e)):
                            self.errors.append(type(e))
                            if self.verbosity >= 2:
                                print(f"Got {type(e).__name__}: {e}")
                    except Exception as e:
                        raise e

    def get_blocks_exception_handler(self, heights: list[int]):
        try:
            asyncio_run(self.__get_blocks_async(heights))
        except concurrent.futures._base.TimeoutError as e:
            if self.verbosity >= 2:
                print(f"Got {type(e).__name__}. Finding failed blocks.")
            required_heights = set(heights)
            loaded_heights = set()
            for height, block_data in self.block_json.items():
                if 'height' in block_data and block_data['height'] == height:
                    loaded_heights.add(height)
            unloaded_heights = required_heights.difference(loaded_heights)
            if self.verbosity >= 2:
                print(f"{len(unloaded_heights)} blocks were not loaded")
            self.failed_heights.update(unloaded_heights)
        except Exception as e:
            raise e

    def __retry_failed_get_blocks_async(self):
        failed_heights = self.failed_heights.copy()
        self.failed_heights = set()
        self.errors = []
        self.get_blocks_exception_handler(list(failed_heights))

    def get_blocks_json(self, heights: list[int]) -> dict[int, dict]:
        retries = 0
        try:
            self.get_blocks_exception_handler(heights)
        except Exception as e:
            raise e
        # retry any failed API requests
        while retries < self.max_retries and self.failed_heights:
            if self.verbosity >= 2:
                print(f'Got {len(self.failed_heights)} errors. Retrying in {self.retry_delay} seconds')
            time.sleep(self.retry_delay)
            try:
                self.__retry_failed_get_blocks_async()
            except Exception as e:
                raise e
            retries += 1

        result = copy.deepcopy(self.block_json)
        self.block_json.clear()
        self.failed_heights = set()
        self.errors = []
        return result

    def get_blocks_json_range(self, min_height: int, max_height: int) -> dict[int, dict]:
        """_summary_

        Args:
            min_height (int)
            max_height (int)
            max_retries (float, optional): How many times to retry if something fails. Defaults to 100.
            retry_delay (int, optional): number of seconds to wait before retrying API calls. Defaults to 10.

        Returns:
            dict[int, dict]: Blockchain data with heights as keys
        """
        return self.get_blocks_json(range(min_height, max_height + 1))


class PersistentBlockchainAPIData(BlockchainDataProviderADT):
    """Persist data from the Blockchain.info API to a database.

    Args:
        BlockchainDataProviderADT (ABC): Implements the abstract
        interface for Bitcoin data providers.
    """
    
    class PopulationStatistics:
        def __init__(self):
            self.total_time = 0
            self.block_population_time = 0
            self.tx_population_time = 0
            self.address_population_time = 0
            self.api_request_time = 0

            self.avg_block_population_time = 0
            self.avg_tx_population_time = 0
            self.avg_address_population_time = 0
            self.avg_api_request_time = 0

            self.total_blocks = 0
            self.total_txs = 0
            self.total_addresses = 0
            self.total_api_requests = 0

        def start_timer(self):
            self.start_time = time.perf_counter()

        def stop_timer(self):
            self.total_time += time.perf_counter() - self.start_time

        def calculate_averages(self):
            if self.total_blocks > 0:
                self.avg_block_population_time = self.block_population_time / self.total_blocks
                self.avg_tx_population_time = self.tx_population_time / self.total_txs
                self.avg_address_population_time = self.address_population_time / self.total_addresses
                self.avg_api_request_time = self.api_request_time / self.total_api_requests

        def __str__(self):
            return f"Total time: {self.total_time}\n" \
                   f"Block population time: {self.block_population_time}\n" \
                   f"Transaction population time: {self.tx_population_time}\n" \
                   f"API request time: {self.api_request_time}\n" \
                   f"Address population time: {self.address_population_time}\n" \
                   f"Average block population time: {self.avg_block_population_time}\n" \
                   f"Average transaction population time: {self.avg_tx_population_time}\n" \
                   f"Average address population time: {self.avg_address_population_time}\n" \
                   f"Average API request time: {self.avg_api_request_time}\n" \
                   f"Total blocks: {self.total_blocks}\n" \
                   f"Total transactions: {self.total_txs}\n" \
                   f"Total addresses: {self.total_addresses}\n" \
                   f"Total API requests: {self.total_api_requests}\n"

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

        self.population_stats = self.PopulationStatistics()

    def get_block(self, session: Session, height: int) -> Block:
        block = session.query(Block) \
            .options(
                joinedload(Block.transactions)
                .joinedload(Tx.inputs)
                .joinedload(Input.prev_out)
                .joinedload(Output.address),
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
            .joinedload(Input.prev_out)
            .joinedload(Output.address),
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

    def get_txs_for_blocks(self, session: Session, min_height: int, max_height: int, buffer: int = 100) -> Generator[Tx, None, None]:

        options = (
            joinedload(Tx.inputs)
            .joinedload(Input.prev_out),
            joinedload(Tx.outputs)
            .joinedload(Output.address)
        )

        tx_count = session.query(Tx.id)\
                          .filter(Tx.block_height <= max_height, Tx.block_height >= min_height)\
                          .count()

        # Iterate through the blocks in the specified range
        for offset in range(0, tx_count, buffer):
            # Fetch transactions in chunks
            txs = session.query(Tx)\
                         .options(options)\
                         .filter(Tx.block_height <= max_height, Tx.block_height >= min_height)\
                         .order_by(Tx.id)\
                         .offset(offset)\
                         .limit(buffer)\
                         .all()
            for tx in txs:
                yield tx

    def get_outputs_for_blocks(self, session: Session, min_height: int, max_height: int, buffer: int = 100) -> Generator[Output, None, None]:
        # Calculate total number of outputs in the height range
        total_outputs = session.query(Output.id) \
                               .join(Tx, Output.tx_id == Tx.id) \
                               .filter(Tx.block_height >= min_height, Tx.block_height <= max_height) \
                               .count()

        for offset in range(0, total_outputs, buffer):
            # Fetch outputs in batches
            outputs_batch = session.query(Output) \
                                   .join(Tx, Output.tx_id == Tx.id) \
                                   .filter(Tx.block_height >= min_height, Tx.block_height <= max_height) \
                                   .order_by(Output.id) \
                                   .offset(offset).limit(buffer).all()

            for output in outputs_batch:
                yield output

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

        address_start_time = time.perf_counter()

        # Use a list to maintain the order of appearance
        ordered_addresses_in_block = [output.address_addr for tx in block.transactions
                                      for output in tx.outputs if output.address_addr is not None]

        # Remove duplicates but preserve order
        unique_ordered_addresses = []
        seen = set()
        for addr in ordered_addresses_in_block:
            if addr not in seen:
                seen.add(addr)
                unique_ordered_addresses.append(addr)

        # Fetch existing addresses in one query
        existing_addresses = session.query(Address).filter(Address.addr.in_(unique_ordered_addresses)).all()
        existing_address_dict = {address.addr: address for address in existing_addresses}

        # Determine which addresses need to be created
        new_addresses = [addr for addr in unique_ordered_addresses if addr not in existing_address_dict]
        new_address_objects = [Address(addr=addr, id=self.current_address_id + i)
                               for i, addr in enumerate(new_addresses)]
        self.current_address_id += len(new_address_objects)

        # Bulk insert new addresses
        session.add_all(new_address_objects)
        # session.bulk_save_objects(new_address_objects)

        # Combine existing and new addresses into one dictionary for easy lookup
        combined_address_dict = {**existing_address_dict, **{addr.addr: addr for addr in new_address_objects}}

        # Update the address objects in outputs
        for tx in block.transactions:
            for output in tx.outputs:
                if output.address_addr:
                    output.address = combined_address_dict.get(output.address_addr)

        self.population_stats.address_population_time += time.perf_counter() - address_start_time
        self.population_stats.total_addresses += len(new_addresses)

    def parse_tx(self, tx_index_in_block: int, json_data: dict,
                 block: Block) -> Tx:

        tx_start_time = time.perf_counter()

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

            # Get prev_out id from the dictionary
            new_input.prev_out_id = self.prev_output_ids_dict[(prev_out_tx_index, prev_out_index_in_tx)]
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

            self.prev_output_ids_dict[(int(tx.index), int(output_idx))] = new_output.id
            tx.outputs.append(new_output)

        self.population_stats.tx_population_time += time.perf_counter() - tx_start_time
        self.population_stats.total_txs += 1

        return tx

    def fetch_previous_output_ids(self, session, json_data: dict):
        # TODO: Test this method
        prev_output_refs = set()
        for tx in json_data['tx']:
            for input in tx['inputs']:
                prev_output_refs.add((int(input['prev_out']['tx_index']), int(input['prev_out']['n'])))

        prev_outputs = session.query(Output.id, Tx.index, Output.index_in_tx)\
            .join(Tx, Output.tx_id == Tx.id)\
            .filter(tuple_(Tx.index, Output.index_in_tx).in_(prev_output_refs))\
            .all()

        return {(tx_index, index_in_tx): output_id for output_id, tx_index, index_in_tx in prev_outputs}

    def parse_block(self, session: Session, height: int = None, json_data: dict = None) -> Block:
        if not (height or json_data):
            raise ValueError("Must provide either height or json_data")
        if not json_data:
            json_data = self.data_provider.get_block_json(height=height)

        block = Block()
        block.height = json_data['height']
        block.transactions = []

        # Fetch IDs for previous outputs not in the current block
        self.prev_output_ids_dict = self.fetch_previous_output_ids(session, json_data)

        for tx_idx, tx_json in enumerate(json_data['tx']):
            self.parse_tx(tx_index_in_block=tx_idx, json_data=tx_json, block=block)

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

    def populate_block(self, session: Session, block_height: int, populate_addresses=True, block_json=None):

        block_start_time = time.perf_counter()

        if block_json is None:
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

        # Populate block data using data provider
        block = self.parse_block(session, height=block_height, json_data=block_json)

        if populate_addresses:
            self.__populate_addresses(session, block)

        # Save block to database
        session.add(block)
        session.commit()
        self.population_stats.block_population_time += time.perf_counter() - block_start_time
        self.population_stats.total_blocks += 1

    def populate_blocks(self,
                        session: Session,
                        block_heights: list[int],
                        show_progressbar=False,
                        fail_if_exists=False):

        self.population_stats = self.PopulationStatistics()
        self.population_stats.start_timer()

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
            block_heights_progressbar = tqdm(block_heights)

        buffer_size = 20
        ranges = chunked_indices(block_heights, buffer_size)

        try:
            for start, end in ranges:
                api_time = time.perf_counter()
                block_json = self.data_provider.get_blocks_json(block_heights[start:end])

                self.population_stats.api_request_time += (time.perf_counter() - api_time)
                self.population_stats.total_api_requests += (end - start)

                for block_height in block_heights[start:end]:
                    self.populate_block(session, block_height, block_json=block_json[block_height])
                    if show_progressbar:
                        block_heights_progressbar.update(1)

        finally:
            self.population_stats.stop_timer()
            self.population_stats.calculate_averages()
            print(self.population_stats)

            if show_progressbar:
                block_heights_progressbar.close()
