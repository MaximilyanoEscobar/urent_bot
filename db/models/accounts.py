from sqlalchemy import Column, Integer, Text, Boolean, BigInteger, ForeignKey, String, JSON
from sqlalchemy.orm import relationship, backref

from db import Base
from db.base import Model


class Accounts(Base, Model):
    """Таблица аккаунтов"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    number = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    coupon = Column(String, nullable=False, unique=True)
    special_field = Column(JSON, nullable=False, default={})
    points = Column(BigInteger, nullable=False, default=0)
    is_delete = Column(Boolean, default=False)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=True)
    user = relationship("User", cascade="all,delete", backref=backref("user", uselist=False), lazy='subquery', foreign_keys=[user_id])

    @property
    def stats(self) -> str:
        """

        :return:
        """
        return ""

    def __str__(self) -> str:
        return f"<Accounts:{self.id}>"

    def __repr__(self):
        return self.__str__()
