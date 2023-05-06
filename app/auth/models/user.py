import random
import re
import string
from datetime import datetime, timedelta
from typing import Optional

from beanie import Document, Indexed
from pydantic import BaseModel, validator

from app.auth.utils.checks import check_phone


class UserAuthCodeInfo(BaseModel):
    phone: str
    expire: datetime = datetime.utcnow() + timedelta(minutes=10)
    can_send: datetime = datetime.utcnow() + timedelta(minutes=3)

    @validator("phone")
    def check_phone(cls, p):
        if len(p) >= 12:
            raise ValueError("The length of the phone number must be less than or equal to 11 characters")

        pattern = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
        if not bool(re.match(pattern, p)):
            raise ValueError("Incorrect phone number format")

        return p


class UserAuthCode(Document, UserAuthCodeInfo):
    """
    Auth code DB representation
    """
    code: str

    @classmethod
    async def get_by_phone(cls, phone: str) -> Optional["UserAuthCode"]:
        """
        Get a user by phone
        :param phone:
        :return:
        """
        return await cls.find_one(cls.phone == phone)


class UserAuth(BaseModel):
    phone: str


class UserUpdate(UserAuth):
    name: Optional[str] = None


def generate_promocode(ln: int):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(ln))


class UserRead(UserUpdate):
    phone: str
    tariff: str = "free"
    tariff_expire: datetime = datetime.utcnow() + timedelta(days=1)
    balance: int = 0
    promocode: str = None

    # validators
    _check_phone = validator("phone", allow_reuse=True)(check_phone)

    @validator("promocode")
    def setup_promocode(cls, pc):
        if not pc:
            return generate_promocode(10)
        return pc


class User(Document, UserRead):
    phone: Indexed(str, unique=True)
    promocode: Indexed(str, unique=True) = None
    @property
    def created(self) -> datetime:
        return self.id.generation_time

    @classmethod
    async def get_by_phone(cls, phone: str):
        return await cls.find_one(cls.phone == phone)

    def __eq__(self, other: "User"):
        return self.phone == other.phone
