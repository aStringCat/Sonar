from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Setting

DATABASE_URL = "sqlite:///./a.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db_setting = db.query(Setting).filter(Setting.key == "similarity_threshold").first()
        if not db_setting:
            default_threshold = Setting(key="similarity_threshold", value="0.85")
            db.add(default_threshold)
            db.commit()
            print("Default similarity threshold (0.85) has been set.")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()