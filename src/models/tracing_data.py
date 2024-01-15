from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    ForeignKey,
    Float,
    CheckConstraint,
    UniqueConstraint
)

from sqlalchemy.orm import relationship, joinedload
import models.base
from bitcoin_data import Tx, Input, Output


class ManualProportion(models.base.Base):
    __tablename__ = 'manual_proportions'
    id = Column(Integer, primary_key=True, autoincrement=True)

    input_id = Column(BigInteger, ForeignKey("transactions.id", ondelete="CASCADE"))

    output_id = Column(BigInteger, ForeignKey("transactions.id", ondelete="CASCADE"))

    # how much of the total possible amount was sent from one input to one output
    # the maximum possible is min(input_value, output_value)
    # by default, the maximum is assumed
    proportion = Column(Float, default=1.0)

    input = relationship("Tx", foreign_keys=[input_id], passive_deletes=True)
    output = relationship("Tx", foreign_keys=[output_id], passive_deletes=True)

    # Check constraint to ensure input and output are in the same transaction
    __table_args__ = (
        CheckConstraint('EXISTS (SELECT 1 FROM transactions t WHERE t.id = input_id AND t.id = output_id)',
                        name='_same_transaction_chk'),
        UniqueConstraint('input_id', 'output_id', name='_input_output_uc'),
    )

    @classmethod
    def get_affected_txs(cls, session):
        """Get all transactions that are affected by the manual proportions.
        """
        options = joinedload(cls.input)\
            .joinedload(Tx.inputs)\
            .joinedload(Input.prev_out)\
            .joinedload(Output.address)\
            .joinedload(cls.output)

        return session.query(Tx)\
                      .options(options)\
                      .join(cls, Tx.id == cls.output_id)\
                      .distinct().all()


class Owner(models.base.Base):
    __tablename__ = 'owners'

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column()

    # Many-to-many relationship with Address
    addresses = relationship("Address", secondary='address_owner_association', back_populates="owners")
    address_associations = relationship("AddressOwnerAssociation", cascade="all, delete-orphan", back_populates="owner")


class AddressOwnerAssociation(models.base.Base):
    __tablename__ = 'address_owner_association'
    address_id = Column(Integer, ForeignKey('addresses.id'), primary_key=True)
    owner_id = Column(Integer, ForeignKey('owners.id'), primary_key=True)

    # Relationships
    address = relationship("Address", back_populates="address_associations")
    owner = relationship("Owner", back_populates="address_associations")
