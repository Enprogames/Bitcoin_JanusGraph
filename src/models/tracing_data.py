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

    proportion = Column(Float)

    input = relationship("Tx", foreign_keys=[input_id], passive_deletes=True)
    output = relationship("Tx", foreign_keys=[output_id], passive_deletes=True)
