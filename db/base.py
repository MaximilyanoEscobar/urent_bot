"""
    Базовые классы базы данных
"""
import datetime

from sqlalchemy import Column, DateTime, func, event  # type: ignore
from sqlalchemy.orm import declarative_base

BaseModel = declarative_base()


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