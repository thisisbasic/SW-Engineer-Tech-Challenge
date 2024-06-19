import os
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SeriesDB(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)
    SeriesInstanceUID = Column(String, index=True, unique=True)
    PatientName = Column(String)
    PatientID = Column(String)
    StudyInstanceUID = Column(String)
    InstancesInSeries = Column(Integer)


Base.metadata.create_all(bind=engine)

app = FastAPI()


class SeriesData(BaseModel):
    SeriesInstanceUID: str
    PatientName: str
    PatientID: str
    StudyInstanceUID: str
    InstancesInSeries: int

    class Config:
        orm_mode = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/series/", response_model=SeriesData)
async def create_series_data(series_data: SeriesData, db: Session = Depends(get_db)):
    logger.info("Received data: %s", series_data)

    # Check for duplication
    existing_series = (
        db.query(SeriesDB)
        .filter(SeriesDB.SeriesInstanceUID == series_data.SeriesInstanceUID)
        .first()
    )
    if existing_series:
        logger.info(
            "Series with UID %s already exists. Ignoring the new data.",
            series_data.SeriesInstanceUID,
        )
        return existing_series

    db_series_data = SeriesDB(**series_data.dict())
    db.add(db_series_data)
    db.commit()
    db.refresh(db_series_data)
    return db_series_data


# @app.get("/series/", response_model=List[SeriesData])
# async def get_all_series_data(db: Session = Depends(get_db)):
#     return db.query(SeriesDB).all()
#
#
# @app.get("/series/{series_instance_uid}", response_model=SeriesData)
# async def get_series_data(series_instance_uid: str, db: Session = Depends(get_db)):
#     series_data = (
#         db.query(SeriesDB)
#         .filter(SeriesDB.SeriesInstanceUID == series_instance_uid)
#         .first()
#     )
#     if series_data is None:
#         raise HTTPException(status_code=404, detail="Series data not found")
#     return series_data
