from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String , Text
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL=os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db        
    finally:
        db.close()       

class BaseSearch(Base):
    __tablename__ = "base_searches"
    id = Column(String, primary_key=True, index=True)
    query = Column(String, index=True)
    response = Column(Text, index=True)
    status = Column(String , default = "queued")

Base.metadata.create_all(bind=engine)    

