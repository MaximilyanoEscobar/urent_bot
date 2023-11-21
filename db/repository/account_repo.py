import secrets
import string

from sqlalchemy import select, update

from db.models.accounts import Accounts


class AccountsRepository:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def add_code(
            self,
            access_token: str,
            refresh_token: str,
            coupon: str,
            special_field: dict,
            number: str,
            points: int = 0,
            user_id: str | None = None):
        async with self.session_maker() as session:
            async with session.begin():
                keys = Accounts(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    coupon=coupon,
                    special_field=special_field,
                    points=points,
                    number=number,
                    user_id=user_id
                )
                try:
                    session.add(keys)
                except Exception:
                    return False
                return True

    async def get_accounts_by_user_id(self, user_id: int, is_delete: bool = False) -> list[Accounts] | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Accounts).where(Accounts.user_id == user_id, Accounts.is_delete == is_delete)
                sql_res = await session.execute(sql)
                return sql_res.scalars().all()

    async def get_accounts(self, is_delete: bool = True) -> list[Accounts] | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Accounts).where(Accounts.is_delete == is_delete)
                sql_res = await session.execute(sql)
                return sql_res.scalars().all()

    async def get_account_by_coupon(self, coupon: str) -> Accounts | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Accounts).where(Accounts.coupon == coupon)
                sql_res = await session.execute(sql)
                return sql_res.scalars().one_or_none()

    async def get_account_by_number(self, number: str) -> Accounts | None:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(Accounts).where(Accounts.number == number)
                sql_res = await session.execute(sql)
                accounts = sql_res.scalars().all()
                return accounts[-1] if accounts else None

    async def update_access_refresh_token(self, _id: int, access_token: str, refresh_token: str):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.refresh_token: refresh_token,
                        Accounts.access_token: access_token
                    }
                ).where(Accounts.id == _id)
                await session.execute(sql)
                await session.commit()

    async def update_access_refresh_token_by_number(self, number: str, access_token: str, refresh_token: str):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.refresh_token: refresh_token,
                        Accounts.access_token: access_token
                    }
                ).where(Accounts.number == number)
                await session.execute(sql)
                await session.commit()

    async def update_account_user_id(self, _id: int, user_id: int):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.user_id: user_id
                    }
                ).where(Accounts.id == _id)
                await session.execute(sql)
                await session.commit()

    async def update_account_status(self, _id: int, is_delete: bool = True):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.is_delete: is_delete
                    }
                ).where(Accounts.id == _id)
                await session.execute(sql)
                await session.commit()

    async def update_account_status_by_number(self, number: str, is_delete: bool = True):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.is_delete: is_delete
                    }
                ).where(Accounts.number == number)
                await session.execute(sql)
                await session.commit()

    async def update_account_status_by_coupon(self, coupon: str, is_delete: bool = True):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.is_delete: is_delete
                    }
                ).where(Accounts.coupon == coupon)
                await session.execute(sql)
                await session.commit()

    async def update_account_special(self, _id: int, special_field: dict):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.special_field: special_field
                    }
                ).where(Accounts.id == _id)
                await session.execute(sql)
                await session.commit()

    async def update_account_points(self, _id: int, points: str):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.points: points
                    }
                ).where(Accounts.id == _id)
                await session.execute(sql)
                await session.commit()

    async def update_used_account_info(self, _id: int, points: float, special_field:dict,  coupon: str = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(16))):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(Accounts).values(
                    {
                        Accounts.coupon: coupon,
                        Accounts.user_id: '',
                        Accounts.points: points,
                        Accounts.special_field: special_field
                    }
                ).where(Accounts.id == _id)
                await session.execute(sql)
                await session.commit()
