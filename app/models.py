from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base
import datetime

class FileMetadata(Base):
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    date_uploaded = Column(DateTime, default=datetime.datetime.utcnow)
    file_format = Column(String)
    columns = Column(String)
    resultado = Column(Text)


