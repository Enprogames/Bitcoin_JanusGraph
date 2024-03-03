from sqlalchemy import (
    Column,
    Index,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    select
)
from sqlalchemy.orm import (
    relationship,
    mapped_column,
    Mapped,
    joinedload,
    aliased
)
import models.base


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


class Block(models.base.Base):
    __tablename__ = 'blocks'
    height = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=True)
    transactions = relationship("Tx", back_populates="block",
                                cascade="all, delete, delete-orphan",
                                order_by="Tx.index_in_block",
                                passive_deletes=True)


class Tx(models.base.Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    hash = Column(String)
    index = Column(BigInteger, index=True)
    index_in_block = Column(Integer, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    block_height = Column(Integer, ForeignKey("blocks.height", ondelete="CASCADE"), index=True)

    block = relationship("Block", back_populates="transactions", passive_deletes=True)
    outputs = relationship("Output", back_populates="transaction",
                           cascade="all, delete, delete-orphan",
                           order_by="Output.index_in_tx",
                           passive_deletes=True)
    inputs = relationship("Input", back_populates="transaction",
                          cascade="all, delete, delete-orphan",
                          order_by="Input.index_in_tx",
                          passive_deletes=True)

    def total_input_value(self):
        if self.is_coinbase():
            return 0

        return sum(input.prev_out.value for input in self.inputs if input.prev_out is not None)

    def pretty_print(self):
        print(f"Tx(id={self.id}, hash={self.hash}, index={self.index})")
        print("Inputs:")
        for input in self.inputs:
            print(f"\t{input.index_in_tx}: {input.prev_out.address.addr[:4]} ({input.prev_out.value / BITCOIN_TO_SATOSHI})")
        print("Outputs:")
        for output in self.outputs:
            print(f"\t{output.index_in_tx}: {output.address.addr[:4]} ({output.value / BITCOIN_TO_SATOSHI})")

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


class Output(models.base.Base):
    __tablename__ = "outputs"

    id: Mapped['int'] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    index_in_tx: Mapped['int'] = mapped_column(Integer)
    value: Mapped['int'] = mapped_column(BigInteger)

    tx_id: Mapped['int'] = mapped_column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"))
    address_id: Mapped['int'] = mapped_column(
        BigInteger,
        ForeignKey("addresses.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )

    # some outputs are unspendable, and we will not be able to
    # find the address for them
    valid: Mapped['bool'] = mapped_column(default=True, index=True)

    transaction: Mapped['Tx'] = relationship(
        back_populates="outputs",
        passive_deletes=True
    )
    address: Mapped['Address'] = relationship(
        back_populates="outputs",
        passive_deletes=True
    )

    # Composite index for efficient querying
    __table_args__ = (
        Index('idx_output_tx_index_in_tx', 'tx_id', 'index_in_tx'),
    )

    def pretty_label(self):
        location = f"{self.transaction.block_height}:{self.transaction.index_in_block}:{self.index_in_tx}"
        value_str = "{:.8f}".format(self.value / BITCOIN_TO_SATOSHI)
        if self.address is None:
            addr_str = "No Address"
        else:
            addr_str = self.address.addr[:4]
        return f"{location} {addr_str} ({value_str})"

    def __repr__(self):
        return f"<Output(id={self.id})>"

    def __str__(self):
        return f"<Output(id={self.id})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id


class Input(models.base.Base):
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
    prev_out_id = Column(Integer, ForeignKey("outputs.id", ondelete="CASCADE"), nullable=True, index=True)
    tx_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"))

    prev_out = relationship("Output", passive_deletes=True)
    transaction = relationship("Tx", back_populates="inputs", passive_deletes=True)

    def pretty_label(self):
        location = f"{self.transaction.block_height}:{self.transaction.index_in_block}:{self.index_in_tx}"
        value_str = "{:.8f}".format(self.prev_out.value / BITCOIN_TO_SATOSHI)
        addr_str = self.prev_out.address.addr[:4]
        return f"{location} {addr_str} ({value_str})"

    def __repr__(self):
        return f"<Input(id={self.id})>"

    def __str__(self):
        return f"<Input(id={self.id})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id


class AddressOwnerAssociation(models.base.Base):
    __tablename__ = 'address_owner_association'
    address_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('addresses.id'), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('owners.id'), primary_key=True)

    address: Mapped['Address'] = relationship(back_populates="owners")
    owner: Mapped['Owner'] = relationship(back_populates="addresses")


class Address(models.base.Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    addr = Column(String, index=True)
    outputs = relationship("Output", back_populates="address", passive_deletes=True)

    # Many-to-many relationship with Owner
    owners: Mapped[list["AddressOwnerAssociation"]] = relationship(back_populates="address")

    def __repr__(self):
        return f"<Address(addr={self.addr})>"

    def __str__(self):
        return f"<Address(addr={self.addr})>"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id


class Owner(models.base.Base):
    __tablename__ = 'owners'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    description = Column(Text, nullable=True)

    # Many-to-many relationship with Address
    addresses: Mapped[list["AddressOwnerAssociation"]] = relationship(back_populates="owner")


class ManualProportion(models.base.Base):
    __tablename__ = 'manual_proportions'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    input_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("inputs.id", ondelete="CASCADE"))

    output_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("outputs.id", ondelete="CASCADE"))

    # how much of the total possible amount was sent from one input to one output
    # the maximum possible is min(input_value, output_value), which will need
    # to be upheld in the application logic.
    # By default, the maximum possible amount is assumed to be sent.
    proportion: Mapped[float] = mapped_column(default=1.0)

    input: Mapped[Input] = relationship(foreign_keys=[input_id], passive_deletes=True)
    output: Mapped[Output] = relationship(foreign_keys=[output_id], passive_deletes=True)

    # Check constraint to ensure input and output are in the same transaction
    # Also ensure proportion is between 0 and 1
    __table_args__ = (
        UniqueConstraint('input_id', 'output_id', name='_input_output_uc'),
        CheckConstraint('proportion >= 0 AND proportion <= 1', name='_proportion_cc'),
    )

    @staticmethod
    def get_affected_txs(session):
        """Get all transactions that are affected by the manual proportions.
        """
        options = (
            joinedload(Tx.inputs)
            .joinedload(Input.prev_out),
            joinedload(Tx.outputs)
        )

        return session.query(Tx) \
                      .options(*options) \
                      .join(Output, Tx.id == Output.tx_id)\
                      .join(ManualProportion, Output.id == ManualProportion.output_id)\
                      .all()
