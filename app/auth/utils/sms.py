from datetime import datetime, timedelta
from random import randint
from typing import Optional

from pydantic import ValidationError
from pyotp import HOTP

from app.auth.models.limits import Limit
from app.auth.models.user import UserAuthCode, UserAuthCodeInfo
from app.auth.sms_api import SMSApi
from app.config import CONFIG
from app.utils import create_counter

hotp = HOTP(CONFIG.auth_secret_key)
sms = SMSApi()
counter = create_counter()


async def create_code() -> str:
    return hotp.at(counter() * randint(0, 1000))


async def send_code(phone: str) -> Optional[UserAuthCodeInfo]:
    old_code = await UserAuthCode.get_by_phone(phone)

    if old_code and old_code.can_send > datetime.utcnow():
        return None

    if old_code:
        await old_code.delete()

    code = await create_code()

    await sms.send(phone, code)

    return await set_code(phone, code)


async def get_code(code: str) -> UserAuthCode | None:
    return await UserAuthCode.find_one(UserAuthCode.code == code)


async def can_send_code(phone: str) -> bool:
    code = await UserAuthCode.get_by_phone(phone)

    if code and code.can_send > datetime.utcnow():
        return False

    return True


async def set_code(phone: str, code: Optional[str] = None) -> UserAuthCodeInfo | ValidationError:
    if code is None:
        code = await create_code()
    try:
        db_code = UserAuthCode(
            code=code,
            phone=phone,
            expire=datetime.utcnow() + timedelta(minutes=10),
            can_send=datetime.utcnow() + timedelta(minutes=3)
        )
        await db_code.create()
    except ValidationError as e:
        return e

    return UserAuthCodeInfo(**db_code.dict())


async def verify_code(code: str) -> UserAuthCode | None:
    code = await get_code(code)

    if not code:
        return None

    await code.delete()

    if code.expire <= datetime.utcnow():
        return None

    return code


async def check_codes() -> None:
    async for i in UserAuthCode.find_all():
        if i.expire <= datetime.utcnow():
            await i.delete()


async def check_limit() -> None:
    async for i in Limit.find_all():
        if i.expire >= datetime.utcnow():
            await i.delete()
