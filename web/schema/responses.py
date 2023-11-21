import dataclasses

from pydantic import BaseModel, Field


@dataclasses.dataclass
class ResponseUploadAccount:
    coupon: str


class CardsOut(BaseModel):
    number: str = Field(..., example="2200123454566767")
    date: str = Field(..., example="10/23")
    cvc: str = Field(..., example="343")