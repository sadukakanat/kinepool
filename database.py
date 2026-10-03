import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# PostgreSQL async connection string with environment variable fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://kinepool_admin:your_secure_password@localhost:5432/kinepool"
)

# 1. Create the asynchronous SQLAlchemy engine with connection pooling[cite: 1]
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,          # Set to True for SQL query debugging in console[cite: 1]
    pool_size=10,        # Permanent connections kept open[cite: 1]
    max_overflow=20      # Extra allowed connections during traffic spikes[cite: 1]
)

# 2. Configure the asynchronous session factory[cite: 1]
SessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 3. Define the Declarative Base for database models[cite: 1]
class Base(DeclarativeBase):
    pass

# 4. Dependency generator for FastAPI routes to safely handle DB transactions[cite: 1]
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise