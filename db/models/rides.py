from sqlalchemy import Column, Integer, Text, Boolean, BigInteger, ForeignKey, String, JSON, DateTime
from sqlalchemy.orm import relationship, backref

from db import BaseModel
from db.base import CleanModel


class Rides(BaseModel, CleanModel):
    """Таблица аккаунтов"""
    __tablename__ = 'rides'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    finished_at = Column(DateTime, nullable=True)
    payment_field = Column(JSON, default={}, nullable=False)
    account_id = Column(BigInteger, ForeignKey('accounts.id'), nullable=False)
    account = relationship("Accounts", cascade="all,delete", backref=backref("acc", uselist=False), lazy='subquery',
                           foreign_keys=[account_id])
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    user = relationship("User", cascade="all,delete", backref=backref("rider", uselist=False), lazy='subquery',
                        foreign_keys=[user_id])
    bot_id = Column(BigInteger, nullable=True)

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
