import secrets
import string

from fastapi import APIRouter, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import Cards
from db.engine import return_session_db, get_db
from db.repository import account_repository, cards_repository
from web.schema.responses import ResponseUploadAccount, CardsOut
from web.schema.schemas import UploadSchema

router = APIRouter(tags=["urent"])


@router.post("/upload/account/", response_model=ResponseUploadAccount)
async def upload_account(
    schema: UploadSchema
):
    coupon = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(16))
    await account_repository.add_code(
        access_token=schema.access_token,
        refresh_token=schema.refresh_token,
        special_field=schema.optional_field,
        number=schema.number,
        coupon=coupon,
        points=schema.points
    )
    return ResponseUploadAccount(coupon=coupon)


@router.get("/db/cards", response_model=Page)
async def get_cards_list(db: AsyncSession = Depends(get_db)):
    response = await paginate(db, select(Cards))
    return response
