from db.engine import return_session_db
from db.repository.account_repo import AccountsRepository
from db.repository.ride_repo import RidesRepository
from db.repository.user_repo import UserRepository
from db.repository.card_repo import CardsRepository

db_session = return_session_db()

user_repository = UserRepository(db_session)
account_repository = AccountsRepository(db_session)
cards_repository = CardsRepository(db_session)
rides_repository = RidesRepository(db_session)
