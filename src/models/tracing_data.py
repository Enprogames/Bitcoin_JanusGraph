from sqlalchemy import (
    Column,
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


class Owner(models.base.Base):
    __tablename__ = 'owners'

    id = Column(Integer, primary_key=True, autoincrement=True)
