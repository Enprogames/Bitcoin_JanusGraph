#!/usr/bin/env python3

from models.base import Base, engine

Base.metadata.create_all(bind=engine)
