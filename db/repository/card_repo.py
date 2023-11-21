from typing import List

from sqlalchemy import select, update

from db.models.accounts import Accounts
from db.models.cards import Cards


class CardsRepository:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def add_card(
            self,
            number: str,
            date: str,
            cvc: str,
            user_id: int | None = None
    ) -> bool:
        async with self.session_maker() as session:
            async with session.begin():
                card = Cards(
                    number=number,
                    date=date,
                    cvc=cvc,
                    user_id=user_id
                )
                try:
                    session.add(card)
                except Exception:
                    return False
                return True

    async def get_card_by_id(self, _id: int) -> Cards | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Cards).where(Cards.id == _id)
                sql_res = await session.execute(sql)
                return sql_res.scalars().one_or_none()

    async def get_card_by_number(self, number: str) -> Cards | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Cards).where(Cards.number == number)
                sql_res = await session.execute(sql)
                return sql_res.scalars().one_or_none()

    async def get_cards_by_user(self, user_id: int, is_deleted: bool = False) -> List[Cards]:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Cards).where(Cards.user_id == user_id, Cards.is_deleted == is_deleted)
                sql_res = await session.execute(sql)
                return sql_res.scalars().all()

    async def update_is_deleted(self, _id: int, is_deleted: bool = True):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Cards).values(
                    {
                        Cards.is_deleted: is_deleted
                    }
                ).where(Cards.id == _id)
                await session.execute(sql)
                await session.commit()
