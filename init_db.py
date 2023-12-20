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

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(engine)  # Creates tables based on your models

    print("Database tables created.")
