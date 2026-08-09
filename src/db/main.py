from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import Config
from sqlmodel.ext.asyncio.session import AsyncSession

async_engine = create_async_engine(
    url=Config.DATABASE_URL, echo=False, pool_size=10, max_overflow=20, pool_timeout=30
)

async_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session