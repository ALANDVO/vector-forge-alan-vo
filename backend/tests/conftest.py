import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_db, close_db, get_session_factory, Base
from app.models.evidence import Base as EvidenceBase


@pytest_asyncio.fixture(scope="function")
async def setup_database():
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session