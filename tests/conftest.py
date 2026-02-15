import pytest
from sqlalchemy.orm import Session
from app.core.database import engine
from app.models.base import Base
import app.models # Ensure all models are registered

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh database session for a test.
    """
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    connection = engine.connect()
    transaction = connection.begin()
    
    session = Session(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback() # Rollback changes after test
        connection.close()
