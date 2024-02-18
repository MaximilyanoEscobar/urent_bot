"""
    Базовые классы базы данных
"""
import datetime
from abc import abstractmethod
from sqlalchemy import Column, DateTime, func, event  # type: ignore
from sqlalchemy.ext.declarative import declarative_base  # type: ignore

Base = declarative_base()


class CleanModel:
    """
        Базовая модель в базе данных
    """
    creation_date = Column(DateTime, nullable=False, default=datetime.date.today())
    upd_date = Column(DateTime, onupdate=datetime.date.today())

    @property
    def no_upd_time(self) -> datetime:
        """
        Получить время, которое модель не обновлялась
        :return: timedelta
        """
        return self.upd_date - datetime.date.today()


def update_created_modified_on_create_listener(mapper, connection, target):
    """ Event listener that runs before a record is updated, and sets the create/modified field accordingly."""
    # it's okay if one of these fields doesn't exist - SQLAlchemy will silently ignore it.
    target.creation_date = datetime.datetime.utcnow()


def update_modified_on_update_listener(mapper, connection, target):
    """ Event listener that runs before a record is updated, and sets the modified field accordingly."""
    # it's okay if this field doesn't exist - SQLAlchemy will silently ignore it.
    target.upd_date = datetime.datetime.utcnow()


event.listen(CleanModel, 'before_insert', update_created_modified_on_create_listener)
event.listen(CleanModel, 'before_update', update_modified_on_update_listener)


class Model(CleanModel):
    """
        Базовая бизнес-модель в базе данных
    """

    @property
    @abstractmethod
    def stats(self) -> str:
        """
        Функция для обработки и получения в строковом формате
        статистики модели (пользователя, ссылки, поста или канала)
        :return:
        """
        ...
