from beanie import Document
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from app.auth.utils.checks import check_phone


class LimitRead(BaseModel):
    phone: str
    limit: int = 10
    expire: datetime = datetime.utcnow() + timedelta(hours=1)

    # validators
    _check_phone = validator("phone", allow_reuse=True)(check_phone)


class Limit(Document, LimitRead):
    @classmethod
    async def get_limit(cls, phone: str) -> "Limit":
        """
        Return Limit instance by phone number

        :param phone:
        :return:
        """
        return await cls.find_one(cls.phone == phone)
