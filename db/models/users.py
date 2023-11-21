from sqlalchemy import Column, Integer, BigInteger, VARCHAR, Boolean

from db import Base
from db.base import Model


class User(Base, Model):
    """Таблица юзеров"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    user_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    username = Column(VARCHAR(50), nullable=True)

    @property
    def stats(self) -> str:
        """

        :return:
        """
        return ""

    def __str__(self) -> str:
        return f"<Users:{self.user_id}>"

    def __repr__(self):
        return self.__str__()