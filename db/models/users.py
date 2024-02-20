from sqlalchemy import Column, Integer, BigInteger, VARCHAR, Boolean

from db import BaseModel
from db.base import CleanModel


class User(BaseModel, CleanModel):
    """Таблица юзеров"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    user_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    username = Column(VARCHAR(50), nullable=True, unique=False)

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