from pydantic import BaseModel, Field


class UploadSchema(BaseModel):
    number: str = Field(title="Номер телефона без + для доступа в аккаунт", max_length=12)
    access_token: str = Field(title="Токен для доступа в аккаунт")
    refresh_token: str = Field(title="Токен для восстановления access")
    optional_field: dict = Field(default={}, title="Доп поля для аккаунта")
    points: int = Field(default=0, title="Баланс аккаунта")