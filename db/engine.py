
"""
    Функции для работы с базой данных
"""
import os
from typing import Union, Iterator

import sqlalchemy.ext.asyncio  # type: ignore
from sqlalchemy import MetaData  # type: ignore
from sqlalchemy.engine import URL  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine, AsyncSession  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore

from configuration import conf


def create_async_engine(url: Union[URL, str]) -> sqlalchemy.ext.asyncio.AsyncEngine:
    """
    :param url:
    :return:
    """
    return _create_async_engine(url=url, echo=bool(os.getenv('debug')), pool_pre_ping=True)


async def proceed_schemas(engine: sqlalchemy.ext.asyncio.AsyncEngine, metadata: MetaData) -> None:
    """

    :param engine:
    :param metadata:
    """
    # async with engine.begin() as conn:
    #     await conn.run_sync(metadata.create_all)
    ...


def get_session_maker(engine: sqlalchemy.ext.asyncio.AsyncEngine) -> sessionmaker:
    """

    :param engine:
    :return:
    """
    return sessionmaker(engine, class_=sqlalchemy.ext.asyncio.AsyncSession, expire_on_commit=False)


def return_session_db():
    async_engine = create_async_engine(conf.db.build_connection_str())
    session_maker = get_session_maker(async_engine)
    return session_maker


async def get_db() -> Iterator[AsyncSession]:
    db = AsyncSession(create_async_engine(conf.db.build_connection_str()))
    async with db.begin():
        yield db
