import datetime
from typing import List

from sqlalchemy import select, update

from db.models.rides import Rides


class RidesRepository:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def add_ride(
            self,
            account_id: int,
            user_id: int,
            payment_field: dict,
            bot_id: int
    ) -> bool:
        async with self.session_maker() as session:
            async with session.begin():
                ride = Rides(
                    account_id=account_id,
                    user_id=user_id,
                    payment_field=payment_field,
                    bot_id=bot_id
                )
                try:
                    session.add(ride)
                except Exception:
                    return False
                return True

    async def update_status_ride_by_kwargs(self, finished_at: datetime.datetime, user_id: int, account_id: int):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Rides).values(
                    {
                        Rides.finished_at: finished_at
                    }
                ).where(Rides.finished_at == None, Rides.user_id == user_id, Rides.account_id == account_id)
                sql_res = await session.execute(sql)
                await session.commit()

    async def get_ride_by_id(self, _id: int) -> Rides | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Rides).where(Rides.id == _id)
                sql_res = await session.execute(sql)
                return sql_res.scalars().one_or_none()

    async def update_finish_ride(self, _id: int, finish_time: datetime.datetime) -> None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Rides).values(
                    {
                        Rides.finished_at: finish_time
                    }
                ).where(Rides.id == _id)
                await session.execute(sql)
                await session.commit()

    async def get_user_rides(self, user_id: int) -> List[Rides]:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Rides).where(Rides.user_id == user_id)
                sql_res = await session.execute(sql)
                return sql_res.scalars().all()

    async def get_all_rides_not_finished(self) -> List[Rides]:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Rides).where(Rides.finished_at == None)
                sql_res = await session.execute(sql)
                return sql_res.scalars().all()

    async def get_all_rides_finished(self) -> List[Rides]:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Rides).where(Rides.finished_at != None)
                sql_res = await session.execute(sql)
                return sql_res.scalars().all()
