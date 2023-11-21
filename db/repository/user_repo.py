from typing import List

from sqlalchemy import select, update

from db.models.users import User


class UserRepository:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def add_user(self, user_id: int, username: str):
        async with self.session_maker() as session:
            async with session.begin():
                user = User(
                    user_id=user_id,
                    username=username
                )
                try:
                    session.add(user)
                except Exception:
                    return False
                return True

    async def get_user(self, user_id: int) -> User:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(User).where(User.user_id == user_id)
                query = await session.execute(sql)
                return query.scalars().one_or_none()

    async def select_all_users(self) -> List[User]:
        async with self.session_maker() as session:
            async with session.begin():
                sql = select(User)
                query = await session.execute(sql)
                return query.scalars().all()

    async def update_username(self, user_id: int, username: str):
        async with self.session_maker() as session:
            async with session.begin():
                sql = update(User).values(
                    {
                        User.username: username
                    }
                ).where(User.user_id == user_id)
                await session.execute(sql)
                await session.commit()
