
from enum import Enum

from pydantic import BaseModel
from beanie import Link

from app.auth.models.user import User


class UserSubscriptions(Enum):
    FREE = "free"
    MONTH = "month"
    WEEK = "week"
    YEAR = "year"


class Promocode(BaseModel):
    value: str
    user: User
    sale: int = 10


class PromocodeRead(BaseModel):
    value: str
    name: str
    sale: int = 10


class PromocodeNotFound(Exception):
    """Promocode not found"""


class UserSubscriptionInvalid(Exception):
    """Invalid user subscribtion"""


async def check_user_sub(user: User, sub: str) -> bool:
    if sub not in [v.value for v in UserSubscriptions]:
        raise UserSubscriptionInvalid

    if user.tariff == sub:
        return True

    return False


async def get_promocode(promocode: str) -> Promocode:
    user = await User.find_one(User.promocode == promocode)

    if not user:
        raise PromocodeNotFound

    if await check_user_sub(user, "free"):
        raise UserSubscriptionInvalid

    return Promocode(value=user.promocode, user=user)
