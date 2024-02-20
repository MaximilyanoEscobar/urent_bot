"""
    Функции для работы с базой данных
"""
from typing import Union

import sqlalchemy.ext.asyncio  # type: ignore
from sqlalchemy import MetaData  # type: ignore
from sqlalchemy.engine import URL  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, \
    create_async_engine as _create_async_engine  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore


def create_async_engine(url: Union[URL, str]) -> AsyncEngine:
    return _create_async_engine(url=url, echo=True, encoding='utf-8', pool_pre_ping=True)


@DeprecationWarning
async def proceed_schemas(engine: AsyncEngine, metadata: MetaData) -> None:
    # async with engine.begin() as conn:
    #     conn.run_sync(metadata.create_all)
    ...


def get_session_maker(engine: AsyncEngine) -> sessionmaker:
    return sessionmaker(engine, class_=AsyncSession)
