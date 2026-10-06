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

Make sure any instructional notes or markdown snippets are kept in your notes or documentation, not inside your source `.py` files!
