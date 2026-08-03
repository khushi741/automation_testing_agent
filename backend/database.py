import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import DATABASE_URL

# Fallback to local SQLite database if PostgreSQL connection fails
try:
    if DATABASE_URL.startswith("postgresql"):
        # Try to create engine and test connection with a short timeout
        engine = create_engine(
            DATABASE_URL, 
            pool_pre_ping=True, 
            pool_size=5, 
            max_overflow=10,
            connect_args={"connect_timeout": 3}
        )
        with engine.connect() as conn:
            pass
        print("Connected to PostgreSQL successfully.")
    else:
        raise ValueError("Not PostgreSQL URL")
except Exception as e:
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_agent.db")
    sqlite_url = f"sqlite:///{sqlite_path}"
    print(f"PostgreSQL connection failed. Falling back to local SQLite database: {sqlite_path}")
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
