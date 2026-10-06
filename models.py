from sqlalchemy import UniqueConstraint, BigInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class DBSubTickAllocation(Base):
    """Ensures unique sub-tick indexing (00-99) per node and integer tick."""
    __tablename__ = "sub_tick_allocations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(10))
    tick_integer: Mapped[int] = mapped_column(BigInteger)   
    sub_counter: Mapped[int] = mapped_column(Integer)
    
    __table_args__ = (UniqueConstraint("node_id", "tick_integer", name="_node_tick_uc"),)

### 2. Initializing & Recreating the Database Index
When deploying a new version model where older schemas need to be cleared or re-indexed:

1. **Drop and Recreate Tables (Prototype Environment):**
   > *Note: `create_all` does not alter pre-existing tables. If updating an older schema layout, drop the existing tables once before letting SQLAlchemy rebuild them[cite: 1].*

2. **Run Schema Creation Programmatically (`main.py` lifespan):**
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       async with engine.begin() as conn:
           # Rebuilds database tables and associated indexes according to Base metadata
           await conn.run_sync(Base.metadata.create_all)
           
           if conn.dialect.name == "postgresql":
               for stmt in APPEND_ONLY_DDL:
                   await conn.execute(text(stmt))
       async with SessionLocal() as db:
           # Seed or verify Master Origin Node (THR / THRINC000)
           ...
       yield
       await engine.dispose()