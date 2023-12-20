from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    ForeignKey
)
from sqlalchemy.orm import relationship
from models.base import Base


BITCOIN_TO_SATOSHI = 1e8

# Since there are only a few duplicate transactions
# on the Bitcoin blockchain, it is worthwhile to just
# directly keep track of them.
#
# We will keep track of the hash and height that the duplication
# occurred at and mark transactions as duplicates while we populate
# if they match these.
#
# My main source is Devin Smith's list of interesting Bitcoin transactions:
# https://github.com/kristovatlas/interesting-bitcoin-data/blob/master/README.md

DUPLICATE_TRANSACTIONS = [
    {
        "block_height": 91842,
        "tx_hash": "d5d27987d2a3dfc724e359870c6644b40e497bdc0589a033220fe15429d88599"
    },
    {
        "block_height": 91880,
        "tx_hash": "e3bf3d07d4b0375638d5f1db5255fe07ba2c4cb067cd81b84ee974b6585fb468"
    }
]


class Block(Base):
    __tablename__ = 'blocks'
    height = Column(Integer, primary_key=True)
    transactions = relationship("Tx", back_populates="block",
                                cascade="all, delete, delete-orphan",
                                order_by="Tx.index_in_block")


class Tx(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    hash = Column(String)
    index = Column(BigInteger, index=True)
    index_in_block = Column(Integer, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    block_height = Column(Integer, ForeignKey("blocks.height"), index=True)

    block = relationship("Block", back_populates="transactions")
    outputs = relationship("Output", back_populates="transaction",
                           cascade="all, delete, delete-orphan",
                           order_by="Output.index_in_tx")
    inputs = relationship("Input", back_populates="transaction",
                          cascade="all, delete, delete-orphan",
                          order_by="Input.index_in_tx")

    def total_input_value(self):
        if self.is_coinbase():
            return 0

        return sum(input.prev_out.value for input in self.inputs if input.prev_out is not None)

    def __repr__(self):
        return f"<Tx(hash={self.hash}, index={self.index})>"

    def __str__(self):
        return f"<Tx(hash={self.hash}, index={self.index})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.hash

    def is_coinbase(self):
        return self.index_in_block == 0


class Output(Base):
    __tablename__ = "outputs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    index_in_tx = Column(Integer)
    value = Column(BigInteger)

    tx_id = Column(Integer, ForeignKey("transactions.id"))
    address_id = Column(Integer, ForeignKey("addresses.id"), index=True)

    # some outputs are unspendable, and we will not be able to
    # find the address for them
    valid = Column(Boolean, default=True, index=True)

    transaction = relationship("Tx", back_populates="outputs")
    address = relationship("Address", back_populates="outputs")
    # inputs = relationship("Input", back_populates="prev_out")

    def __repr__(self):
        return f"<Output(value={self.value})>"

    def __str__(self):
        return f"<Output(value={self.value})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id


class Input(Base):
    __tablename__ = "inputs"

    """Each output should have a unique ID.

    My plan is to enumerate outputs from the start and apply an
    ID to each one in the order they appear in the blockchain.

    Args:
        output (Output): The output to get the ID for.

    Returns:
        int
    """
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    index_in_tx = Column(Integer)
    prev_out_id = Column(Integer, ForeignKey("outputs.id"), nullable=True, index=True)
    tx_id = Column(Integer, ForeignKey("transactions.id"))

    prev_out = relationship("Output")
    transaction = relationship("Tx", back_populates="inputs")

    def __repr__(self):
        return f"<Input(id={self.id})>"

    def __str__(self):
        return f"<Input(id={self.id})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    addr = Column(String, index=True)
    outputs = relationship("Output", back_populates="address")

    def __repr__(self):
        return f"<Address(addr={self.addr})>"

    def __str__(self):
        return f"<Address(addr={self.addr})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id
