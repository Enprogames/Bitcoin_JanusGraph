#!/usr/bin/env python3

import argparse

from dotenv import load_dotenv

from blockchain_data_provider import (
    PersistentBlockchainAPIData,
    BlockchainAPIJSON,
    BLOCKCHAIN_INFO_BLOCK_ENDPOINT
)

from models.base import SessionLocal
from models.bitcoin_data import Block

# see if database tables exist. if not, create them
from models import base
from sqlalchemy import inspect
from sqlalchemy.sql import text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script for populating database")
    parser.add_argument('--height', default=None, type=int, help='Block height up to which to populate')
    parser.add_argument('-e', '--endpoint', default=BLOCKCHAIN_INFO_BLOCK_ENDPOINT,
                        type=str, help='API endpoint for blockchain data population')
    parser.add_argument('--delete', default=False, action='store_true', help='Delete all data in database before populating')

    args = parser.parse_args()

    args.delete

    inspector = inspect(base.engine)

    if args.delete:
        print("Deleting all data in database...")
        # wipe the database
        with SessionLocal() as session:
            if inspector.has_table("inputs"):
                session.execute(text('DELETE FROM inputs'))
            if inspector.has_table("outputs"):
                session.execute(text('DELETE FROM outputs'))
            if inspector.has_table("transactions"):
                session.execute(text('DELETE FROM transactions'))
            if inspector.has_table("blocks"):
                session.execute(text('DELETE FROM blocks'))
            if inspector.has_table("addresses"):
                session.execute(text('DELETE FROM addresses'))
            session.commit()

        print("Database wiped.")

    if not inspector.has_table("blocks"):
        print("No data found. Database created.")

    load_dotenv()

    if args.height is not None:

        with SessionLocal() as session:
            highest_block = session.query(Block).order_by(Block.height.desc()).first()

        if args.endpoint == BLOCKCHAIN_INFO_BLOCK_ENDPOINT:
            print("Using default blockchain.info endpoint.")
        else:
            print(f"Using endpoint {args.endpoint}...")

        if highest_block is not None:
            print(f"Current highest block: {highest_block.height}")
            highest_block = highest_block.height
        else:
            print("No blocks found in database. Populating from genesis block...")
            highest_block = 0

        if args.height < highest_block:
            print(f"Specified height {args.height} is lower than current highest block {highest_block}. Exiting.")
            exit(1)
        elif args.height == highest_block:
            print(f"Specified height {args.height} is equal to current highest block {highest_block}. Exiting.")
        else:
            print(f"Populating up to height {args.height}...")
            slow_provider = BlockchainAPIJSON(block_endpoint=args.endpoint)
            provider = PersistentBlockchainAPIData(data_provider=slow_provider)
            with SessionLocal() as session:
                provider.populate_blocks(session, range(0, args.height+1), show_progressbar=True)
            print("Done.")
