import sys
from pathlib import Path

container_src_path = Path('/app/src/')
local_src_path = Path(Path.cwd(), 'src/')

# see if this src path exists.
# if it does, we are in a container.
# if not, we are in local.
if not container_src_path.exists():
    src_path = local_src_path
else:
    src_path = container_src_path

src_path_str = str(src_path)
if src_path_str not in sys.path:
    sys.path.insert(0, src_path_str)

from models.base import Base, engine
# All models must be imported in this file
# Otherwise, SQLAlchemy won't know about them
from models.bitcoin_data import Block, Tx, Input, Output, Address

import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from models.base import Base, engine

max_retries = 5
retry_interval = 10  # seconds


def wait_for_db():
    retries = 0
    while retries < max_retries:
        try:
            # Try to connect to the database
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))  # This query will throw an exception if the database is not ready
            print("Connected to database.")
            return
        except OperationalError:
            retries += 1
            print(f"Database not ready. Waiting for {retry_interval} seconds. Retry {retries}/{max_retries}")
            time.sleep(retry_interval)
    print("Failed to connect to the database after several retries.")
    sys.exit(1)


def create_tables():
    Base.metadata.create_all(engine)  # Creates tables based on your models


if __name__ == "__main__":
    # Wait for the database to be ready
    wait_for_db()
    print("Creating database tables...")
    create_tables()

    print("Database tables created.")
