from sqlalchemy import (
    Column,
    CheckConstraint,
    Integer,
    BigInteger,
    ForeignKey,
    Float
)
from sqlalchemy.orm import relationship
import models.base


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
                        name='chk_same_transaction'),
    )


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
