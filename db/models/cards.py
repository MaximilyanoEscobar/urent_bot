from sqlalchemy import Column, Integer, Text, Boolean, BigInteger, ForeignKey, String, JSON
from sqlalchemy.orm import relationship, backref

from db import Base
from db.base import Model


class Cards(Base, Model):
    """Таблица аккаунтов"""
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    number = Column(String, nullable=False)
    date = Column(String, nullable=False)
    cvc = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=True)
    user = relationship("User", cascade="all,delete", backref=backref("cum", uselist=False), lazy='subquery', foreign_keys=[user_id])

    @property
    def stats(self) -> str:
        """

        :return:
        """
        return ""

    def __str__(self) -> str:
        return f"<Cards:{self.id}>"

    def __repr__(self):
        return self.__str__()
