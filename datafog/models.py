from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ValueMapping(Base):
    __tablename__ = 'value_mapping'  # make sure this is the actual name of your table in the DB

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer)
    field_name = Column(String, nullable=False)
    original_value = Column(String, nullable=False)
    new_value = Column(String, nullable=False)
