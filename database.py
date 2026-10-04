import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase


def _build_url_and_args():
    raw = os.getenv("DATABASE_URL")
    if not raw:
        if os.getenv("KINEPOOL_DEV_SQLITE") == "1":
            return "sqlite+aiosqlite:///./kinepool_dev.db", {}
        raise RuntimeError(
            "DATABASE_URL is not set. Set it to your PostgreSQL URL "
            "(or set KINEPOOL_DEV_SQLITE=1 for local development only)."
        )
    # Render/Heroku style URLs -> asyncpg driver
    for prefix in ("postgres://", "postgresql://"):
        if raw.startswith(prefix):
            raw = "postgresql+asyncpg://" + raw[len(prefix):]
            break
    connect_args = {}
    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query))
    # asyncpg does not understand ?sslmode=...; translate it.
    sslmode = query.pop("sslmode", None)
    if sslmode and sslmode != "disable":
        connect_args["ssl"] = True
    raw = urlunsplit(parts._replace(query=urlencode(query)))
    return raw, connect_args


DATABASE_URL, _CONNECT_ARGS = _build_url_and_args()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

_engine_kwargs = {"echo": False, "connect_args": _CONNECT_ARGS}
if not IS_SQLITE:
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """One session per request. Handlers commit explicitly."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise